from functools import lru_cache

from api.infrastructure.configuration import Configuration


@lru_cache
def get_configuration() -> Configuration:
    return Configuration()


configuration = get_configuration()
