# ADR — Batch mode for chat completions

* **Status:** Proposed
* **Date:** 2026-11-11
* **Authors:** Thomas Guillory
* **Related:**
  * Proof of concept: branch [`feat/batch-mode`](https://github.com/thomasguillory-betagouv/OpenGateLLM/tree/feat/batch-mode) of a fork, [diff against `main`](https://github.com/thomasguillory-betagouv/OpenGateLLM/compare/main...feat/batch-mode) (code, tests, benchmark script [`2026-11-11-batch-mode-benchmark.py`](https://github.com/thomasguillory-betagouv/OpenGateLLM/blob/feat/batch-mode/adr/scripts/2026-11-11-batch-mode-benchmark.py))
  * Reference API: [Anthropic Message Batches](https://platform.claude.com/docs/en/build-with-claude/batch-processing)
  * [#656 — Batch endpoint](https://github.com/etalab-ia/OpenGateLLM/issues/656), [#999 — ADR - Batch endpoint stack](https://github.com/etalab-ia/OpenGateLLM/issues/999)
  * The QoS ADR ([#1123](https://github.com/etalab-ia/OpenGateLLM/pull/1123), `adr/2026-09-02-qos.md`, since folded into the documentation by [#1180](https://github.com/etalab-ia/OpenGateLLM/pull/1180)), which announced this ADR
  * [#531 — ADR - Request priorization + QoS without worker and rabbitmq](https://github.com/etalab-ia/OpenGateLLM/issues/531), [#1398 — Weighted provider load](https://github.com/etalab-ia/OpenGateLLM/issues/1398)
* **Decision Outcome:** _pending review_. Proposal: add an asynchronous batch API for chat completions, modeled on Anthropic's Message Batches, processed by an optional worker that only uses the provider capacity interactive traffic leaves free.

---

## Context

### The step after QoS

The QoS ADR (#1123) set apart three related needs: prioritization, QoS, and batch — "launching jobs when the providers have spare capacity" — and announced a dedicated ADR for the last one: batch needs a load indicator, and QoS provides it (`load(p)`, the Redis count of the requests each provider holds). Issue #999 opened that ADR with two questions: pull or push, one worker or several.

This ADR is that one. It answers pull, with as many workers as needed (decisions 2 and 3), and it admits batch requests on the QoS load (decision 4). It keeps the constraint #531 set when Celery and RabbitMQ were removed: Postgres and Redis remain the only mandatory dependencies.

### Bulk workloads compete with interactive users

OpenGateLLM fronts GPU servers (mostly vLLM) that are provisioned for the interactive peak. Part of the traffic is not interactive at all: classifying or extracting data from a corpus, summarizing documents, evaluating a model, generating synthetic data. Nobody waits for these results in front of a screen; they only need them "today".

Today the only way to run such a job is to loop over `POST /v1/chat/completions`. The gateway then treats each of these requests exactly like a user's chat message:

* The provider QoS (`qos_limit` + `qos_retries_before_reject`) protects the providers from overload, but it has no notion of priority: an interactive request waits in the same reservation retry loop as the bulk requests, and is rejected with a 503 just as often.
* Rate limits (RPM/TPM) are the only lever left, and they cap the bulk job without protecting the other users.
* The client has to implement concurrency control, retries and resumption itself, and keep connections open for the whole job.

### A concrete need: API Projets Collectivités

API Projets Collectivités (DINUM) classifies stocks of local government projects with Gemma 4 31B on Albert API, the main OpenGateLLM deployment. Its workloads:

| Workload | Volume | Latency constraint |
|---|---|---|
| Full reclassification of the project stock | ~1M requests every 4 to 6 months | None, as long as the job ends in reasonable time |
| New data source, partial reclassification | ~100k requests a month, up to 300k for a new source | None |
| Daily run | ~10k requests a day | Regular API calls |

These jobs run today on a non-sovereign provider, where the full reclassification takes a few hours, and the team wants to move them to a sovereign stack. With the quotas of a production role on Albert API (100 RPM, 50,000 RPD), the daily limit alone stretches the full reclassification over 20 days, and the per-minute limit makes iterating on a prompt impractical.

The deployment already answers such needs, by hand: a temporary "night shift" role (1,000 RPM, no daily limit, to be used at night), granted by the team for two or three one-shot runs. It works, but it does not scale: each run needs a person on both sides, the night is a proxy for spare capacity rather than a measure of it, and nothing stops such a job from competing with interactive users when the night is not as quiet as expected. A batch mode does the same thing without the manual step, and only uses the capacity that is actually free.

How often other users ask for the same thing is for the Albert API team to say (see "To be checked by the maintainers").

### Measured impact (synthetic benchmark)

The proof of concept ships a benchmark ([`adr/scripts/2026-11-11-batch-mode-benchmark.py`](https://github.com/thomasguillory-betagouv/OpenGateLLM/blob/feat/batch-mode/adr/scripts/2026-11-11-batch-mode-benchmark.py), on the proof of concept branch: it runs against its code). A mock provider stands for a GPU server: it computes 8 requests at a time, 0.5 s each (16 requests/s at most), and OpenGateLLM fronts it with `qos_limit: 8` and `qos_retries_before_reject: 20`. Interactive traffic arrives at random (Poisson) for 30 s while a 300-request job runs. The job is sent either as users send it today, looping over `/v1/chat/completions` with 32 concurrent requests and a retry on 503, or as a batch. Within a run, every scenario replays the same interactive arrivals, so the rows of a table differ only by the job. The run is repeated three times with other arrivals: the tables give the median of the three runs with their range in parentheses, and the failures summed over the three runs.

An interactive request that finds the provider full retries its reservation every 0.5 s: it is answered in about 0.54 s when served at once, 1.04 s after one retry, and so on. A percentile close to such a step jumps from one value to the next on a handful of requests: interactive traffic alone at 50 % load has a p95 of 0.60 s in one run and 1.09 s in another. The "waited" column is steadier: the share of interactive requests answered after more than 0.75 s, failed ones included, that is the ones that waited at least one retry.

**Interactive traffic at 4 requests/s (about 25 % of the capacity, 98 to 121 requests per run)**

| Scenario | Interactive p50 | p95 | p99 | Waited | Interactive failed | Job duration |
|---|---|---|---|---|---|---|
| Interactive traffic alone | 0.54 s | 0.58 s (0.57–0.60) | 0.60 s (0.57–0.62) | 0.0 % (0.0–0.0) | 0 / 323 | — |
| + job looping over `/v1/chat/completions` | 1.55 s | **7.19 s** (6.58–7.67) | **9.29 s** (8.80–10.31) | **68.4 %** (66.3–77.7) | **11 / 323** | 29.5 s |
| + same job submitted as a batch | 0.54 s | **0.57 s** (0.56–0.58) | **0.59 s** (0.57–0.62) | **0.8 %** (0.0–1.0) | **0 / 323** | 58.9 s |
| Batch alone (no interactive traffic) | — | — | — | — | — | 42.6 s |

**Interactive traffic at 8 requests/s (about 50 % of the capacity, 226 to 245 requests per run)**

| Scenario | Interactive p50 | p95 | p99 | Waited | Interactive failed | Job duration |
|---|---|---|---|---|---|---|
| Interactive traffic alone | 0.55 s | 1.05 s (0.60–1.09) | 1.15 s (1.09–1.17) | 6.6 % (3.1–9.0) | 0 / 712 | — |
| + job looping over `/v1/chat/completions` | 2.06 s | **9.58 s** (9.17–9.83) | **10.84 s** (10.33–10.87) | **87.8 %** (84.2–90.7) | **83 / 712** | 39.4 s |
| + same job submitted as a batch | 0.55 s | **1.07 s** (0.60–1.08) | **1.45 s** (1.07–1.58) | **9.8 %** (4.4–11.2) | **0 / 712** | 68.4 s |

Every batch request succeeded. A bulk job sent the way users send it today makes most interactive requests wait (68 % at 25 % load, 88 % at 50 %), multiplies their p95 by about 12 and 9 (7.19 s against 0.58 s, 9.58 s against 1.05 s), and makes 3 % and 12 % of them fail (11 of 323, 83 of 712).

The same job sent as a batch makes no interactive request fail and leaves their median and p95 at the level of interactive traffic alone, but it is not free: interactive requests wait a little more often. At 25 % load, 2 of 323 waited one retry, against none alone. At 50 % load, summed over the three runs, 61 of 712 waited instead of 45 (8.6 % against 6.3 %), more in each run (10 against 7, 24 against 22, 27 against 16), and the median p99 rises from 1.15 s to 1.45 s (higher in two runs of three). A batch request is admitted only while the provider holds fewer than 4 requests, but it keeps its place until it ends: interactive requests arriving in a burst meanwhile can find up to 4 places taken, and some of them wait for the next retry. The capacity share (open question 3) sets this cost against batch throughput.

The batch takes longer than the looping job because it only uses the capacity left over, and it slows down as interactive load grows: 43 s alone, 59 s next to 25 % load, 68 s next to 50 %.

These numbers come from a mock provider on a single machine. They show the mechanism, not production capacity. Real figures need a run against a staging vLLM.

### Market reference

Anthropic (Message Batches) and OpenAI (Batch API) both offer an asynchronous mode: requests are processed within 24 hours, at half price, and the results are downloaded once the batch has ended. Developers know this contract.

---

## Decision

| # | Decision |
|---|---|
| 1 | Add an **asynchronous batch API for chat completions**, modeled on Anthropic's Message Batches: requests sent inline with a `custom_id`, `processing_status` `in_progress` → `canceling` → `ended`, `request_counts`, JSONL results, cancellation, expiration after 24 h. |
| 2 | **Persist batches in Postgres** and use it as the queue (`FOR UPDATE SKIP LOCKED` + lease). No new dependency. |
| 3 | **Process batches in a separate, optional worker process** (`python -m api.worker`, same image as the API), scaled by replicas. |
| 4 | **Batch requests only use spare capacity**: they go through the same provider concurrency limiter as interactive requests, with a lower limit. |
| 5 | **Reuse the forwarding pipeline**: routing, access control, provider selection, usage, cost and carbon footprint are those of `POST /v1/chat/completions`. |

### 1. API

| Anthropic | OpenGateLLM | Notes |
|---|---|---|
| `POST /v1/messages/batches` | `POST /v1/chat/completions/batches` | `{"requests": [{"custom_id", "params"}]}`, `params` being a `/v1/chat/completions` body; `stream: true` is rejected. The models are checked at creation (exists, `text-generation`, user has access). |
| `GET /v1/messages/batches/{id}` | `GET /v1/chat/completions/batches/{batch_id}` | `object: "batch"`, `processing_status`, `request_counts {processing, succeeded, errored, canceled, expired}`, `created`, `expires`, `ended`, `cancel_initiated`. |
| `GET /v1/messages/batches` | `GET /v1/chat/completions/batches` | Paginated with `offset`/`limit`, like every list of the API. |
| `POST /v1/messages/batches/{id}/cancel` | `POST /v1/chat/completions/batches/{batch_id}/cancel` | Pending requests are canceled at once, requests in progress run to the end. |
| `GET /v1/messages/batches/{id}/results` | `GET /v1/chat/completions/batches/{batch_id}/results` | JSON Lines, one `{"custom_id", "result": {"type", "response", "error"}}` per request, available once the batch has ended. |
| `DELETE /v1/messages/batches/{id}` | `DELETE /v1/chat/completions/batches/{batch_id}` | Final implementation, not in the POC. Deletes an ended batch with its requests and results; 409 for a batch in progress or canceling, which has to be canceled first. The retention purge (open question 5) deletes ended batches the same way. |

The path nests the batch under the endpoint it batches, as Anthropic does. It leaves `/v1/batches` free for an OpenAI-compatible façade (see alternatives) and makes room for `/v1/embeddings/batches`. The new `RouterName.BATCHES` can be disabled like any router.

Inline requests rather than OpenAI's file upload: OpenGateLLM has no file storage, and the Anthropic contract needs none.

### 2. Storage and queue

Two tables: `batch` (owner, key, status, timestamps) and `batch_request` (one row per request: `custom_id`, `position`, `params`, `status`, `attempts`, `available_at`, `locked_until`, `response`, `error`). Request counts are aggregated at read time.

Postgres is the queue. Redis cannot be: gunicorn flushes it at every API start (`scripts/gunicorn.conf.py`), and it is not configured for durability.

* **Claim**: one `UPDATE … WHERE id IN (SELECT … FOR UPDATE SKIP LOCKED) RETURNING …` statement marks requests `processing`, gives each a `claim_id` and a lease (`locked_until`). Several workers never claim the same request. Only requests of batches `in_progress` are claimed.
* **Lease**: the worker extends the leases of the requests it is processing every 20 s (lease: 60 s), so a claim stays valid however long the provider takes, and expires about a minute after its worker dies.
* **Crash safety**: a request whose lease expires goes back to the queue and counts an attempt, so a request that kills its worker is not retried forever. The outcome is written only by the holder of the current `claim_id`: a worker whose claim expired cannot overwrite the result of the worker that claimed the request again.
* **Billed once**: the usage row of a succeeded request is written in the same statement as its result (`UPDATE … RETURNING` in a CTE, then `INSERT INTO usage … SELECT`), conditioned on the claim. A request processed twice is billed once, by the worker whose result is stored.
* **Fairness**: requests are claimed lowest `position` first (rank of the request in its batch), so a small batch submitted after a large one is not stuck behind it. The flip side: under a steady inflow of new batches, the tail of a large batch waits, and may expire.
* Every worker-side statement is a single statement on an `AutocommitSession`: the worker never holds a transaction, nor a pooled connection, during a provider call.

### 3. Worker

`api/worker.py` is a new composition root, like `lifespan.py`. `BatchWorker` (`api/infrastructure/worker/`) claims up to `batch_worker_concurrency` requests, processes them concurrently, extends their leases, and runs a periodic reconciliation step: release expired claims, cancel the requests that went back to the queue after their batch was canceled, expire the pending requests of overdue batches, end finished batches. On SIGTERM it stops claiming and waits up to 30 s for the requests in progress; the ones it interrupts go back to the queue when their claim expires.

The worker is optional, and the reconciliation runs inside it: without a worker, batches are accepted and stay `in_progress` indefinitely.

It runs from the API image with another command, so it adds a service to deploy but no dependency. For small deployments, the same loop could also run inside the API process, behind a setting (not in the POC): one service less, at the cost of sharing the API's CPU and shutdown (see alternative G).

### 4. Spare capacity only

The provider concurrency limiter counts every request a provider holds, interactive or batch, in one Redis sorted set. Interactive requests reserve a place while the load is below `qos_limit`. Batch requests reserve one only while the load is below `batch_provider_capacity_share × qos_limit` rounded down (0.5 by default: 4 places out of 8, none out of 1), or below `batch_provider_default_concurrency` for providers without `qos_limit`.

* Interactive traffic always keeps at least the rest of the capacity, and takes all of it when batch requests are not running.
* A batch request never waits for a provider and never gets a 429: without spare capacity it goes back to the queue and the worker pauses its claims briefly.
* When Redis is unreachable and the load cannot be read, batch requests wait. Interactive requests keep failing open, as today.
* A transient provider failure (timeout, 429, 5xx) is retried with exponential backoff, up to 3 attempts. Other failures end the request as `errored`.
* The rule reads whatever load the limiter counts. Once it counts a weighted workload instead of requests (#1398), batch requests are capped in tokens with no change here.

### 5. Reuse

`ProcessBatchRequestUseCase` subclasses `ProviderRequestForwardingUseCase` with its own `execute()`. Its flow differs (never wait, requeue instead of 503), as `CreateChatCompletionsUseCase` does for streaming. It reuses `_get_usable_router`, `_order_by_strategy`, `_get_billed_tokens`, `_compute_usage` and `_record_and_save_usage`. Access is checked again at processing time: a revoked key, an expired user or a model whose access was removed fails the request.

Each succeeded request writes a regular `usage` row with `endpoint = /v1/chat/completions/batches`, so `GET /v1/usage` can filter batch consumption.

---

## Alternatives considered

| Option | Description | Decision |
|---|---|---|
| A | Do nothing: users loop over `/v1/chat/completions` | Rejected: see the benchmark. |
| B | A priority on the interactive endpoint (header, or `user.priority` in the QoS) | Complementary, not a substitute: the client still holds connections and implements retries and resumption. Still worth doing later. |
| C | OpenAI-compatible `/v1/files` + `/v1/batches` | Deferred. Works with the OpenAI SDK, but needs a Files API and object storage (a new dependency). The queue, the worker and the capacity rule (about 80 % of the work) are the same, so this façade can be added on top later. |
| D | **Anthropic-style inline batches** | **Selected**: no file storage, a contract developers know. |
| E | Delegate to provider-native batch APIs (OpenAI, Mistral) | Out of scope: self-hosted vLLM has no online batch API. Could be an adapter later for external providers. |
| F | A job queue library (Celery, arq, procrastinate) | Not needed: the Postgres queue fits in one repository class. Celery or arq would add a broker; procrastinate (Postgres-based) remains an option if the queue grows more complex. |
| G | Run the worker inside the API processes (lifespan task) | Not as the default: it couples batch load with API latency, multiplies workers by `gunicorn workers × replicas`, and constrains shutdown. Worth offering as an option for small deployments, which then have no service to add. |
| H | A separate orchestrator with Celery, S3 and Redis priority queues (the draft attached to #999) | Rejected: it brings back the broker and the extra service that #531 and #1131 removed, and its orchestrator calls the providers directly, outside the QoS limiter. It shares one idea with this ADR: Postgres holds the state. Its two needs are kept: audio batches (plan, step 5) and interactive traffic ranked below batch (open question 9). |

---

## Consequences

**Becomes easier**

* Bulk jobs no longer make interactive requests fail, and only slightly increase how often they wait (see the benchmark); they use the GPUs when interactive traffic is low.
* Users get a managed asynchronous API: no concurrency control, retries or resumption to write, and results kept server-side.
* Batch consumption is visible in `GET /v1/usage` and can be priced on its own.

**Becomes harder**

* One more process to deploy and monitor (the worker), with its own Helm/compose service.
* Two more tables, whose size grows with the results kept: a retention period and a purge job are needed.
* At-least-once provider calls: if a worker dies after the provider answered but before the result is stored, another worker sends the request again. It is billed once, since its usage row is written with its result, but the GPU time of the first call is lost. Calling the provider exactly once would need an idempotency key on the provider side, which vLLM does not offer; the window is the few milliseconds between the provider's answer and the write.
* Maintenance surface: the POC adds about 1,900 lines of production code and 1,450 lines of tests.

---

## Proof of concept

The POC on branch [`feat/batch-mode`](https://github.com/thomasguillory-betagouv/OpenGateLLM/tree/feat/batch-mode) implements decisions 1–5 for chat completions, with unit tests for every use case branch and for the worker loop, integration tests for the repository, the endpoints and the migration, and the benchmark above. The existing test suite passes unchanged. An independent code review found two state-transition bugs (a stale outcome overwriting a newer one after a lease expiry, canceled batches still processing their requeued requests), fixed in the POC.

Not in the POC (needed before production):

* **quotas for batches (blocking)**: the POC neither checks nor charges any rate limit for batch requests, so a user with an RPD limit could bypass it through a batch. The router must ship disabled until open question 1 is settled;
* a batch price (open question 2);
* retention and purge of results, and `DELETE` (decision 1);
* Prometheus metrics (queue depth, batch throughput), Langfuse traces for batch requests (the worker uses a no-op tracer);
* the `test_autocommitsession.py`-style probe for the worker;
* claiming per router: a worker currently claims before knowing whether the router has spare capacity, and pauses all claims when one router is full;
* refactoring rather than copying: `ProcessBatchRequestUseCase` copies the provider reservation loop of the forwarding template with another limit, and carries a rate limiter it never calls. Passing the limit to the template, and moving `UsageRecorder` out of `infrastructure/fastapi/`, would remove both;
* Helm/compose service, documentation, playground page, `AGENTS.md` section on the worker.

---

## To be checked by the maintainers

The author has no access to these data; they decide how much capacity a batch mode would actually find, and how many users it would serve.

1. **GPU utilization** over a typical week (the `vllm` Grafana dashboards): how much capacity is idle per model, between the peaks of office hours as well as at night. Batch requests use spare capacity whenever it appears, not only at night.
2. **Demand**: how many users have asked for higher quotas, for the night shift role, or for a batch mode, and for which volumes.
3. **Ongoing work**: #999 was closed in September 2026 without a batch ADR in the repository, and no branch or pull request implements one. Its draft, a Celery orchestrator with S3 and Redis priority queues, predates the removal of Celery; this ADR replaces it (alternative H).
4. **A run on a staging vLLM**: the figures above come from a mock. The benchmark script can target a real provider instead (`--provider-url`, `--provider-model`, `--slots` for its `qos_limit`).

---

## Open questions for the maintainers

1. **Rate limits (blocking).** The POC neither checks nor charges RPM/TPM/RPD/TPD for batch requests; Anthropic keeps separate batch limits. Should batches count toward the daily limits (TPD/RPD)? Should a new limit type cap the number of pending batch requests per user or role?
2. **Price.** A batch discount (a multiplier on the router cost, global or per router)?
3. **Capacity share.** Is 50 % of `qos_limit` the right default? Should it be configurable per router? What should the default be for providers without `qos_limit`?
4. **Fairness unit.** Batches are interleaved by progress. Should fairness be per user or per organization instead, and should it use `user.priority`?
5. **Limits and retention.** 10,000 requests per batch in the POC (Anthropic: 100,000 or 256 MB, too heavy to parse in an API worker). How long are results kept (Anthropic: 29 days)?
6. **URL.** `/v1/chat/completions/batches` (proposed) or `/v1/batches`?
7. **Results errors.** The POC reports domain error names (`ModelNotFoundError`, `StatusCodeModelError`…). Do we want a public error taxonomy?
8. **Deployment.** Is a separate worker service acceptable for the deployments we know of (Albert, others), or should the embedded mode (alternative G) come first?
9. **Interactive traffic below batch.** The draft of #999 ranked some interactive traffic (sync priority 4) below batch. Is that a need, for guest accounts for instance? It belongs to the prioritization ADR announced by the QoS ADR; this ADR ranks batch below all interactive traffic.

---

## Plan if accepted

1. Domain, tables, repository (Postgres queue).
2. API endpoints, router disabled by default.
3. Worker and capacity-capped processing.
4. Quotas, price, retention and purge, metrics, deployment and documentation.
5. Later: playground page, `/v1/embeddings/batches`, audio transcription batches (they need file storage: an audio file does not fit in a JSON body, hence the S3 of the #999 draft), OpenAI-compatible façade, provider-native batch adapters.
