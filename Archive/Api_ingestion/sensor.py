from dataclasses import dataclass, field

from Archive.Api_ingestion.constants import (
    STATE_CRITICAL,
    STATE_NORMAL,
    STATE_WARNING,
)
from Archive.Api_ingestion.exceptions import SensorError
from Archive.Api_ingestion.sensor_state import NormalState, SensorState


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

    def __post_init__(self):
        """Valide les données après initialisation."""
        if self.anomalies_count < 0:
            raise SensorError("Le nombre d'anomalies ne peut pas être négatif.")
        if self.value < 0:
            raise SensorError("La valeur du capteur ne peut pas être négative.")

    def set_state(self, new_state: SensorState) -> None:
        """
        Change l'état du capteur.

        Args:
            new_state: Nouvel état

        Raises:
            SensorError: Si le nouvel état est invalide
        """
        if not isinstance(new_state, SensorState):
            raise SensorError(f"État invalide : {type(new_state)}")
        self.state = new_state

    def update_anomalies_count(self, count: int) -> None:
        """
        Met à jour le nombre d'anomalies et réévalue l'état.

        Args:
            count: Nouveau nombre d'anomalies

        Raises:
            SensorError: Si count est négatif
        """
        if count < 0:
            raise SensorError("Le nombre d'anomalies ne peut pas être négatif.")

        self.anomalies_count = count
        self.evaluate_state()

    def evaluate_state(self) -> None:
        """Demande à l'état courant de gérer les anomalies."""
        self.state.handle_anomalies(self)

    def get_state_name(self) -> str:
        """Retourne le nom de l'état courant."""
        return self.state.name()

    def is_normal(self) -> bool:
        """Vérifie si le capteur est en état NORMAL."""
        return self.get_state_name() == STATE_NORMAL

    def is_warning(self) -> bool:
        """Vérifie si le capteur est en état WARNING."""
        return self.get_state_name() == STATE_WARNING

    def is_critical(self) -> bool:
        """Vérifie si le capteur est en état CRITICAL."""
        return self.get_state_name() == STATE_CRITICAL