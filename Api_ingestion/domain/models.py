from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class SensorStatus(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


def _iso(ts: Optional[datetime]) -> Optional[str]:
    return ts.isoformat() if isinstance(ts, datetime) else None


@dataclass
class Sensor:
    sensor_id: str
    sensor_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    _last_value: Optional[float] = field(default=None, init=False, repr=False)
    _last_unit: Optional[str] = field(default=None, init=False, repr=False)
    _last_timestamp: Optional[datetime] = field(default=None, init=False, repr=False)
    _anomaly_streak: int = field(default=0, init=False, repr=False)
    _status: SensorStatus = field(default=SensorStatus.NORMAL, init=False, repr=False)

    @property
    def status(self) -> SensorStatus:
        return self._status

    @property
    def anomaly_streak(self) -> int:
        return self._anomaly_streak

    def update(
        self,
        *,
        value: Optional[float] = None,
        unit: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        is_anomaly: bool = False,
    ) -> SensorStatus:
        # maj des valeurs internes (encapsulation)
        if value is not None:
            self._last_value = value
        if unit is not None:
            self._last_unit = unit
        self._last_timestamp = timestamp or self._last_timestamp or datetime.utcnow()

        # logique d'anomalies consécutives
        if is_anomaly:
            self._anomaly_streak += 1
        else:
            self._anomaly_streak = 0

        # transition d'état
        if self._anomaly_streak >= 3:
            self._status = SensorStatus.CRITICAL
        elif self._anomaly_streak >= 1:
            self._status = SensorStatus.WARNING
        else:
            self._status = SensorStatus.NORMAL

        return self._status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "sensor_type": self.sensor_type,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "last_value": self._last_value,
            "last_unit": self._last_unit,
            "last_timestamp": _iso(self._last_timestamp),
            "status": self._status.value,
            "anomaly_streak": self._anomaly_streak,
        }


@dataclass(frozen=True)
class PollutionReading:
    city: str
    pollutant: str
    value: float
    unit: str
    latitude: Optional[float]
    longitude: Optional[float]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = _iso(self.timestamp)
        return d


@dataclass(frozen=True)
class TrafficReading:
    city: str
    jam_factor: float
    current_speed: float
    free_flow_speed: float
    confidence: float
    latitude: Optional[float]
    longitude: Optional[float]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = _iso(self.timestamp)
        return d