from abc import ABC, abstractmethod

from Archive.Api_ingestion.constants import (
    MAX_ANOMALIES_WARNING,
    MIN_ANOMALIES_WARNING,
    STATE_CRITICAL,
    STATE_NORMAL,
    STATE_WARNING,
)


class SensorState(ABC):
    """Interface pour un état de capteur."""

    @abstractmethod
    def name(self) -> str:
        """Nom de l'état."""
        pass

    @abstractmethod
    def handle_anomalies(self, sensor: "Sensor") -> None:
        """
        Gère l'anomalie et effectue la transition si nécessaire.

        Args:
            sensor: Instance du capteur à mettre à jour
        """
        pass


class NormalState(SensorState):
    """État normal du capteur (pas ou peu d'anomalies)."""

    def name(self) -> str:
        return STATE_NORMAL

    def handle_anomalies(self, sensor: "Sensor") -> None:
        """
        Depuis Normal :
        - 1-2 anomalies → WARNING
        - >2 anomalies → CRITICAL
        """
        if MIN_ANOMALIES_WARNING <= sensor.anomalies_count <= MAX_ANOMALIES_WARNING:
            sensor.set_state(WarningState())
        elif sensor.anomalies_count > MAX_ANOMALIES_WARNING:
            sensor.set_state(CriticalState())


class WarningState(SensorState):
    """État d'avertissement du capteur (anomalies modérées)."""

    def name(self) -> str:
        return STATE_WARNING

    def handle_anomalies(self, sensor: "Sensor") -> None:
        """
        Depuis Warning :
        - 0 anomalies → NORMAL
        - >2 anomalies → CRITICAL
        """
        if sensor.anomalies_count == 0:
            sensor.set_state(NormalState())
        elif sensor.anomalies_count > MAX_ANOMALIES_WARNING:
            sensor.set_state(CriticalState())


class CriticalState(SensorState):
    """État critique du capteur (beaucoup d'anomalies)."""

    def name(self) -> str:
        return STATE_CRITICAL

    def handle_anomalies(self, sensor: "Sensor") -> None:
        """
        Depuis Critical :
        - 0 anomalies → NORMAL
        - 1-2 anomalies → WARNING
        """
        if sensor.anomalies_count == 0:
            sensor.set_state(NormalState())
        elif MIN_ANOMALIES_WARNING <= sensor.anomalies_count <= MAX_ANOMALIES_WARNING:
            sensor.set_state(WarningState())