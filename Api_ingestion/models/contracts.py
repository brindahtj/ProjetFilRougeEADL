from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Literal
import uuid


Pollutant = Literal["no2", "pm25", "pm10", "o3", "co"]

Severity = Literal[
    "LOW",
    "MEDIUM",
    "HIGH"
]


@dataclass
class AirQualityAlertEvent:

    event_id: str

    city: str

    pollutant: Pollutant

    value: float

    threshold: float

    severity: Severity

    # Pollution
    unit: str

    # Traffic correlation
    jam_factor: float
    current_speed: float
    free_flow_speed: float

    # Metadata
    timestamp: str

    @staticmethod
    def create(
        city: str,
        pollutant: Pollutant,
        value: float,
        threshold: float,
        unit: str,
        jam_factor: float,
        current_speed: float,
        free_flow_speed: float,
    ):

        if value >= threshold * 1.5:
            severity = "HIGH"

        elif value >= threshold * 1.2:
            severity = "MEDIUM"

        else:
            severity = "LOW"

        return AirQualityAlertEvent(
            event_id=str(uuid.uuid4()),

            city=city,

            pollutant=pollutant,

            value=value,

            threshold=threshold,

            severity=severity,

            unit=unit,

            jam_factor=jam_factor,

            current_speed=current_speed,

            free_flow_speed=free_flow_speed,

            timestamp=datetime.utcnow().isoformat(),
        )

    def to_dict(self):
        return asdict(self)