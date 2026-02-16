from dataclasses import dataclass


@dataclass
class RouterAliasAlreadyExistsError:
    aliases: list[str]


@dataclass
class RouterNameAlreadyExistsError:
    name: str


@dataclass
class RouterNotFoundError:
    router_id: int
