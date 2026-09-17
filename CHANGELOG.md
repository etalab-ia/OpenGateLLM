# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file was introduced during the `0.7.0` cycle and only covers releases from there on. For earlier history, see the
[commit log](https://github.com/etalab-ia/OpenGateLLM/commits/main).

## [Unreleased]

### Removed

- **Breaking — the search tool is gone from `POST /v1/chat/completions`.** The OpenGateLLM `search` tool extension
  (`tools: [{"type": "search", ...}]`) and the `search_results` field it added to responses and to the final streamed
  chunk are removed. Integrators now compose OpenGateRAG (search) then OpenGateLLM (chat), or put a reverse proxy in
  front of both. See [`adr/2026-07-01-split-rag.md`](adr/2026-07-01-split-rag.md). The tool was deprecated in `0.5.0`;
  removal was announced for `1.0.0` and lands earlier.
- **Breaking — the `search_opengaterag_url` setting is removed.** It only powered the search tool above. Configuration
  files that still carry the key keep starting: it is ignored rather than rejected.

### Changed

- Streamed chat completions announce the **router** name in every chunk. Data chunks were relayed verbatim and carried the
  provider's internal model id, while the final usage chunk already carried the router name — a single stream contradicted
  itself. Clients reading `model` from a streamed delta now see the name they asked for.
- `POST /v1/chat/completions` validates `messages` at the API boundary. An entry that is not an object is now rejected
  with `422` and a Pydantic error body, where it was previously forwarded to the model provider and surfaced as the
  provider's own `400`.

### Fixed

- Environmental impacts (`kwh`, `kgco2eq`) are recorded again in usage rows for `/v1/embeddings`, `/v1/ocr`,
  `/v1/rerank` and `/v1/audio/transcriptions`. They were computed and returned in the response body, but persisted as
  `NULL`, so they were missing from `GET /v1/usage` for those endpoints.
