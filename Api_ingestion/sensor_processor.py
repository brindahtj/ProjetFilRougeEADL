import logging
from typing import Dict, Optional
from datetime import datetime

from Api_ingestion.domain import Sensor, SensorStatus, PollutionReading, TrafficReading

log = logging.getLogger(__name__)


class SensorStreamProcessor:
    """Gère l'état des capteurs et détecte les anomalies."""

    def __init__(self, pollution_threshold: float = 50.0, traffic_threshold: float = 0.8):
        self.sensors: Dict[str, Sensor] = {}
        self.pollution_threshold = pollution_threshold
        self.traffic_threshold = traffic_threshold

    def process_pollution_reading(self, reading: PollutionReading) -> SensorStatus:
        sensor_id = f"pollution_{reading.city}_{reading.pollutant}"

        if sensor_id not in self.sensors:
            self.sensors[sensor_id] = Sensor(
                sensor_id=sensor_id,
                sensor_type="pollution",
                latitude=reading.latitude,
                longitude=reading.longitude,
            )

        sensor = self.sensors[sensor_id]
        is_anomaly = reading.value > self.pollution_threshold

        status = sensor.update(
            value=reading.value,
            unit=reading.unit,
            timestamp=reading.timestamp,
            is_anomaly=is_anomaly,
        )

        if is_anomaly:
            log.warning(
                "Anomalie pollution détectée : %s (valeur=%f, état=%s)",
                sensor_id,
                reading.value,
                status.value,
            )

        return status

    def process_traffic_reading(self, reading: TrafficReading) -> SensorStatus:
        sensor_id = f"traffic_{reading.city}"

        if sensor_id not in self.sensors:
            self.sensors[sensor_id] = Sensor(
                sensor_id=sensor_id,
                sensor_type="traffic",
                latitude=reading.latitude,
                longitude=reading.longitude,
            )

        sensor = self.sensors[sensor_id]
        is_anomaly = reading.jam_factor > self.traffic_threshold

        status = sensor.update(
            value=reading.jam_factor,
            unit="jam_factor",
            timestamp=reading.timestamp,
            is_anomaly=is_anomaly,
        )

        if is_anomaly:
            log.warning(
                "Anomalie trafic détectée : %s (jam_factor=%f, état=%s)",
                sensor_id,
                reading.jam_factor,
                status.value,
            )

        return status

    def get_sensors_by_status(self, status: SensorStatus) -> Dict[str, Sensor]:
        return {sid: s for sid, s in self.sensors.items() if s.status == status}

    def get_critical_sensors(self) -> Dict[str, Sensor]:
        return self.get_sensors_by_status(SensorStatus.CRITICAL)