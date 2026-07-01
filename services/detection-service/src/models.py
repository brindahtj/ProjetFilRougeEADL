from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class PollutionMessage(BaseModel):
    city: str
    zone: Optional[str] = None
    pollutant: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timestamp: Optional[datetime] = None

class TrafficMessage(BaseModel):
    city: str
    zone: Optional[str] = None
    street: Optional[str] = None
    section_id: Optional[str] = None
    q: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timestamp: Optional[datetime] = None

class AlertEvent(BaseModel):
    type: str            # pollution | traffic | correlation
    level: str           # WARNING | CRITICAL
    title: str
    message: str
    city: Optional[str] = None
    zone: Optional[str] = None
    street: Optional[str] = None
    section_id: Optional[str] = None
    pollutant: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    source: Optional[str] = "detection-service"
    metadata: Optional[Dict[str, Any]] = {}