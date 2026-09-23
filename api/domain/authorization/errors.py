from dataclasses import dataclass


@dataclass
class UnauthorizedActionError:
    subject: str
    relation: str
    object: str
