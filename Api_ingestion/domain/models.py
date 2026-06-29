from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any


def _iso(dt: datetime) -> str:
    return dt.isoformat() if isinstance(dt, datetime) else str(dt)


@dataclass(frozen=True)
class PollutionReading:
    location: str
    parameter: str
    value: float
    unit: str
    timestamp: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = _iso(self.timestamp)
        return d


@dataclass(frozen=True)
class TrafficReading:
    sensor_id: str
    speed: float
    vehicle_count: Optional[int]
    timestamp: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = _iso(self.timestamp)
        return d
