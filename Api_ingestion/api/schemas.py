from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any


@dataclass
class ZoneSchema:
    id: str
    name: str
    latitude: float
    longitude: float
    type: str
    createdAt: datetime


@dataclass
class SensorSchema:
    id: str
    name: str
    type: str
    zoneId: str
    latitude: float
    longitude: float
    status: str
    anomalyStreak: int
    lastValue: Optional[float] = None
    lastUnit: Optional[str] = None
    lastTimestamp: Optional[datetime] = None


@dataclass
class MetricSchema:
    id: str
    sensorId: str
    zoneId: str
    type: str
    value: float
    unit: str
    timestamp: datetime
    isAnomaly: bool


@dataclass
class MetricCreateSchema:
    sensorId: str
    type: str
    value: float
    unit: str
    timestamp: datetime
    isAnomaly: bool = False




@dataclass
class ErrorDetail:
    code: str
    message: str
    status: int
    resource: Optional[str] = None
    timestamp: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    retryable: bool = False
    retryAfterSeconds: Optional[int] = None
    correlationId: Optional[str] = None