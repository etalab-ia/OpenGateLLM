from pydantic import Field

from api.schemas import BaseModel


class EnvironmentalImpacts(BaseModel):
    kWh: float = Field(default=0.0, description="Carbon footprint in kWh.")
    kgCO2eq: float = Field(default=0.0, description="Carbon footprint in kgCO2eq (global warming potential).")


class CarbonFootprintUsageKWh(BaseModel):
    min: float = Field(default=0.0, description="Minimum carbon footprint in kWh.", deprecated=True)
    max: float = Field(default=0.0, description="Maximum carbon footprint in kWh.", deprecated=True)


class CarbonFootprintUsageKgCO2eq(BaseModel):
    min: float = Field(default=0.0, description="Minimum carbon footprint in kgCO2eq (global warming potential).", deprecated=True)
    max: float = Field(default=0.0, description="Maximum carbon footprint in kgCO2eq (global warming potential).", deprecated=True)


class CarbonFootprintUsage(BaseModel):
    kWh: CarbonFootprintUsageKWh = Field(default_factory=CarbonFootprintUsageKWh, deprecated=True)
    kgCO2eq: CarbonFootprintUsageKgCO2eq = Field(default_factory=CarbonFootprintUsageKgCO2eq, deprecated=True)


class Usage(BaseModel):
    prompt_tokens: int = Field(default=0, description="Number of prompt tokens (e.g. input tokens).")
    completion_tokens: int = Field(default=0, description="Number of completion tokens (e.g. output tokens).")
    total_tokens: int = Field(default=0, description="Total number of tokens (e.g. input and output tokens).")
    cost: float = Field(default=0.0, description="Total cost of the request.")
    carbon: CarbonFootprintUsage = Field(default_factory=CarbonFootprintUsage, deprecated=True)
    impacts: EnvironmentalImpacts = Field(default_factory=EnvironmentalImpacts)
    requests: int = Field(default=0, description="Number of model requests.")
