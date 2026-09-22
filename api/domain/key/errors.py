from dataclasses import dataclass


@dataclass
class KeyExpirationInvalidError:
    max_expiration_days: int


@dataclass
class KeyNotFoundError:
    id: int
