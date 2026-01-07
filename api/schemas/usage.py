from pydantic import Field

from api.schemas import BaseModel


class CarbonFootprintUsageKWh(BaseModel):
    min: float = Field(default=0.0, description="Minimum carbon footprint in kWh.")
    max: float = Field(default=0.0, description="Maximum carbon footprint in kWh.")


class CarbonFootprintUsageKgCO2eq(BaseModel):
    min: float = Field(default=0.0, description="Minimum carbon footprint in kgCO2eq (global warming potential).")
    max: float = Field(default=0.0, description="Maximum carbon footprint in kgCO2eq (global warming potential).")


class CarbonFootprintUsage(BaseModel):
    kWh: CarbonFootprintUsageKWh = Field(default_factory=CarbonFootprintUsageKWh)
    kgCO2eq: CarbonFootprintUsageKgCO2eq = Field(default_factory=CarbonFootprintUsageKgCO2eq)


class Usage(BaseModel):
    prompt_tokens: int = Field(default=0, description="Number of prompt tokens (e.g. input tokens).")
    completion_tokens: int = Field(default=0, description="Number of completion tokens (e.g. output tokens).")
    total_tokens: int = Field(default=0, description="Total number of tokens (e.g. input and output tokens).")
    cost: float = Field(default=0.0, description="Total cost of the request.")
    carbon: CarbonFootprintUsage = Field(default_factory=CarbonFootprintUsage)
    requests: int = Field(default=0, description="Number of model requests.")
