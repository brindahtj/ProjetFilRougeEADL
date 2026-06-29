from dataclasses import dataclass, field

from Api_ingestion.exceptions import SensorError
from Api_ingestion.sensor_state import NormalState, SensorState


@dataclass
class Sensor:
    city: str
    pollutant: str
    value: float
    unit: str
    latitude: float
    longitude: float
    timestamp: str
    anomalies_count: int = 0
    state: SensorState = field(default_factory=NormalState)

    def set_state(self, state: SensorState) -> None:
        self.state = state

    def update_anomalies(self, count: int) -> None:
        if count < 0:
            raise SensorError("Le nombre d'anomalies ne peut pas être négatif.")
        self.anomalies_count = count
        self.state.handle_anomalies(self)

    def get_state_name(self) -> str:
        return self.state.name()

    def is_normal(self) -> bool:
        return self.get_state_name() == "NORMAL"

    def is_warning(self) -> bool:
        return self.get_state_name() == "WARNING"

    def is_critical(self) -> bool:
        return self.get_state_name() == "CRITICAL"