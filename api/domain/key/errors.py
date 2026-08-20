from dataclasses import dataclass


@dataclass
class KeyAlreadyExistsError:
    name: str


@dataclass
class KeyNotFoundError:
    id: int
