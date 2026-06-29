from abc import ABC, abstractmethod


class SensorState(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def handle_anomalies(self, sensor: "Sensor") -> None:
        pass


class NormalState(SensorState):
    def name(self) -> str:
        return "NORMAL"

    def handle_anomalies(self, sensor: "Sensor") -> None:
        if 1 <= sensor.anomalies_count <= 2:
            sensor.set_state(WarningState())
        elif sensor.anomalies_count > 2:
            sensor.set_state(CriticalState())


class WarningState(SensorState):
    def name(self) -> str:
        return "WARNING"

    def handle_anomalies(self, sensor: "Sensor") -> None:
        if sensor.anomalies_count == 0:
            sensor.set_state(NormalState())
        elif sensor.anomalies_count > 2:
            sensor.set_state(CriticalState())


class CriticalState(SensorState):
    def name(self) -> str:
        return "CRITICAL"

    def handle_anomalies(self, sensor: "Sensor") -> None:
        if sensor.anomalies_count == 0:
            sensor.set_state(NormalState())
        elif 1 <= sensor.anomalies_count <= 2:
            sensor.set_state(WarningState())