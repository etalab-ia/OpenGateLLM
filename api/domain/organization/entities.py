from dataclasses import dataclass
from datetime import datetime


@dataclass
class Organization:
    id: int
    name: str
    users: int
    created: datetime
    updated: datetime
