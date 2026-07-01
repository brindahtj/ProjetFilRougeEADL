from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ThresholdResponse(BaseModel):
    id: int
    key: str
    value: float
    pollutant: Optional[str] = None
    metric: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    version: int = 1
    active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ThresholdCreate(BaseModel):
    key: str
    value: float
    pollutant: Optional[str] = None
    metric: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None