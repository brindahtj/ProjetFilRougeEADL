from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PollutionReading:
    city: str
    pollutant: str
    value: float
    unit: str
    latitude: float
    longitude: float
    timestamp: str


@dataclass
class TrafficReading:
    """Modèle trafic pour API Paris OpenData."""
    city: str
    street: str
    section_id: str
    q: float
    etat_trafic: str
    latitude: float
    longitude: float
    timestamp: str
    upstream_name: Optional[str] = None
    downstream_name: Optional[str] = None