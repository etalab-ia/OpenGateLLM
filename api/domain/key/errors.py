from dataclasses import dataclass


@dataclass
class KeyAlreadyExistsError:
    name: str


@dataclass
class KeyExpirationInvalidError:
    max_expiration_days: int


@dataclass
class KeyNotFoundError:
    id: int
