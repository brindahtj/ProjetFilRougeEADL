from pydantic import BaseModel, Field

class SensorMetricIn(BaseModel):
    metric: str
    value: float
    unit: str
    recorded_at: str

class SensorMetricsResult(BaseModel):
    status: str = Field(default="accepted")
    processed_count: int