from dataclasses import dataclass


@dataclass
class InvalidKeyError:
    pass


@dataclass
class KeyNotFoundError:
    id: int
