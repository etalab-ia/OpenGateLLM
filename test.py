import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import threading
import time

from openai import APIStatusError, OpenAI
from redis import Redis

base_url = "http://localhost:8000/v1"
api_key = "sk-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo0LCJ0b2tlbl9pZCI6MiwiZXhwaXJlcyI6MTc4OTg1NTIwMH0.NWDHaFc0dAa8I269xwadZum5RnUrUIYMeEuKCATYuRY"
QOS_LOAD_PREFIX = "ogl_qos:load"
INFLIGHT_PREFIX = "ogl_mg:inflight"


def connect_redis() -> Redis:
    return Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD", "changeme"),
        decode_responses=True,
    )


def format_load(r: Redis) -> str:
    qos_parts = []
    for key in sorted(r.scan_iter(f"{QOS_LOAD_PREFIX}:*")):
        members = r.zrange(key, 0, -1, withscores=True)
        provider_id = key.rsplit(":", 1)[-1]
        request_ids = [member for member, _score in members]
        qos_parts.append(f"p={provider_id} load={len(members)} ids={request_ids}")

    inflight_parts = []
    for key in sorted(r.scan_iter(f"{INFLIGHT_PREFIX}:*")):
        provider_id = key.rsplit(":", 1)[-1]
        inflight_parts.append(f"p={provider_id} inflight={r.get(key)}")

    qos = " | ".join(qos_parts) if qos_parts else "{}"
    inflight = " | ".join(inflight_parts) if inflight_parts else "{}"
    return f"load(p)={qos}  ogl_mg:inflight={inflight}"


def print_load(r: Redis, label: str) -> None:
    print(f"{label}: {format_load(r)}", flush=True)


def one_chat(i: int, client: OpenAI, r: Redis) -> None:
    print_load(r, f"req #{i} start")
    try:
        response = client.chat.completions.create(
            model="test",
            messages=[{"role": "user", "content": "Hello, world!"}],
        )
        preview = (response.choices[0].message.content or "").replace("\n", " ")[:80]
        print_load(r, f"req #{i} stop ({preview!r})")
    except APIStatusError as exc:
        retry_after = exc.response.headers.get("Retry-After") if exc.response is not None else None
        if exc.status_code == 503:
            print_load(r, f"req #{i} stop ERROR 503 Retry-After={retry_after}")
        else:
            print_load(r, f"req #{i} stop ERROR {exc.status_code}: {exc.message}")
    except Exception as exc:
        print_load(r, f"req #{i} stop ERROR: {exc}")


def poll_load(r: Redis, stop: threading.Event) -> None:
    last = None
    while not stop.wait(0.1):
        rendered = format_load(r)
        if rendered != last:
            print(f"[poll] {rendered}", flush=True)
            last = rendered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("n", type=int, nargs="?", default=5, help="nombre de requêtes en parallèle")
    args = parser.parse_args()

    client = OpenAI(base_url=base_url, api_key=api_key, max_retries=0)
    r = connect_redis()

    print_load(r, "avant")
    stop = threading.Event()
    poller = threading.Thread(target=poll_load, args=(r, stop), daemon=True)
    poller.start()

    with ThreadPoolExecutor(max_workers=args.n) as pool:
        futures = []
        for i in range(args.n):
            futures.append(pool.submit(one_chat, i, client, r))
            if i < args.n - 1:
                time.sleep(1)
        for future in as_completed(futures):
            future.result()

    stop.set()
    poller.join(timeout=1)
    print_load(r, "fin")


if __name__ == "__main__":
    main()
