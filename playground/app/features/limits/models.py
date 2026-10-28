from pydantic import BaseModel


class Limit(BaseModel):
    type_label: str = ""
    used: str = ""
    value: str = ""
    percent: int = 0
    is_unlimited: bool = False


class ModelLimits(BaseModel):
    model: str = ""
    limits: list[Limit] = []
