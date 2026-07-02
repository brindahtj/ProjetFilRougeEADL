from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime

class RawMeasurement(BaseModel):
    type: Literal["pollution", "traffic"]
    city: str
    zone: Optional[str] = None
    pollutant: Optional[str] = None
    value: Optional[float] = None
    street: Optional[str] = None
    section_id: Optional[str] = None
    q: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timestamp: Optional[datetime] = None

class ValidationResult(BaseModel):
    state: Literal["NORMAL", "CRITICAL"]
    valid: bool
    measurement: Optional[RawMeasurement] = None
    errors: list[str] = []
    warnings: list[str] = []