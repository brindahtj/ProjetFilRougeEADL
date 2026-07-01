from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PollutionMeasurement(BaseModel):
    city: str
    zone: Optional[str]
    pollutant: str
    value: float
    latitude: Optional[float]
    longitude: Optional[float]
    timestamp: datetime

class TrafficMeasurement(BaseModel):
    city: str
    zone: Optional[str]
    street: str
    section_id: str
    q: float
    latitude: Optional[float]
    longitude: Optional[float]
    timestamp: datetime

class AssociatedData(BaseModel):
    city: str
    zone: Optional[str]
    pollution_count: int
    traffic_count: int
    pollution_avg: float
    traffic_avg: float
    time_window: str  # "HH:MM"
    timestamp: datetime