from dataclasses import dataclass


@dataclass
class RouterAliasAlreadyExistsError:
    pass


@dataclass
class RouterNameAlreadyExistsError:
    name: str


@dataclass
class InsufficientPermissionError:
    pass
