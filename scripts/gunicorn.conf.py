from prometheus_client import multiprocess
from redis import Redis as SyncRedis

from api.utils.configuration import get_configuration


def on_starting(server):
    client = SyncRedis.from_url(get_configuration().dependencies.redis.url)
    try:
        client.flushdb()
        server.log.info("Redis keys flushed on API startup.")
    finally:
        client.close()


def child_exit(server, worker):
    multiprocess.mark_process_dead(worker.pid)
