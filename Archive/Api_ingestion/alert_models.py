from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field



class AlertType(str, Enum):
    pollution = "pollution"
    traffic = "traffic"
    correlation = "correlation"


class AlertLevel(str, Enum):
    warning = "WARNING"
    critical = "CRITICAL"


class AlertBase(BaseModel):
    type: AlertType
    level: AlertLevel
    title: str
    message: str
    city: Optional[str] = None
    zone: Optional[str] = None
    street: Optional[str] = None
    pollutant: Optional[str] = None
    value: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True



class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    type: Optional[AlertType] = None
    level: Optional[AlertLevel] = None
    title: Optional[str] = None
    message: Optional[str] = None
    city: Optional[str] = None
    zone: Optional[str] = None
    street: Optional[str] = None
    pollutant: Optional[str] = None
    value: Optional[float] = None
    active: Optional[bool] = None


class Alert(AlertBase):
    id: int