from dataclasses import dataclass


@dataclass
class InvalidKeyError:
    pass


@dataclass
class KeyAlreadyExistsError:
    name: str


@dataclass
class KeyNotFoundError:
    id: int
