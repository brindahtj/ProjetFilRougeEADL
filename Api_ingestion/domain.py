from dataclasses import dataclass


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
    city: str
    jam_factor: float
    current_speed: float
    free_flow_speed: float
    confidence: float
    latitude: float
    longitude: float
    timestamp: str