from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class RawMeasurement(BaseModel):
    type: Literal["pollution", "traffic"]
    city: str
    zone: Optional[str] = None
    pollutant: Optional[str] = None   # for pollution
    value: Optional[float] = None     # for pollution
    street: Optional[str] = None      # for traffic
    section_id: Optional[str] = None  # for traffic
    q: Optional[float] = None         # traffic metric
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timestamp: Optional[datetime] = None