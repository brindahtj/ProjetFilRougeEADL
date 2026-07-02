import logging
from typing import Dict, List, Optional
from datetime import datetime
from uuid import uuid4

from Api_ingestion.domain import Sensor, SensorStatus, PollutionReading, TrafficReading
from Api_ingestion.monitoring import metrics
from Api_ingestion.sensor_processor import SensorStreamProcessor
from Api_ingestion.api.schemas import ZoneSchema, SensorSchema, MetricSchema, MetricCreateSchema
from Api_ingestion.config import ZONES

log = logging.getLogger(__name__)


class ZoneController:
    def __init__(self):
        self.zones: Dict[str, ZoneSchema] = self._init_zones()

    @staticmethod
    def _init_zones() -> Dict[str, ZoneSchema]:
        """Initialiser les zones à partir de la config"""
        zones = {}
        for zone in ZONES:
            zone_id = f"zone-{zone['name'].lower()}"
            zones[zone_id] = ZoneSchema(
                id=zone_id,
                name=zone["name"],
                latitude=zone["lat"],
                longitude=zone["lon"],
                type="urban",
                createdAt=datetime.utcnow(),
            )
        return zones

    def get_all_zones(self) -> List[ZoneSchema]:
        return list(self.zones.values())

    def get_zone_by_id(self, zone_id: str) -> Optional[ZoneSchema]:
        return self.zones.get(zone_id)

    def create_zone(self, name: str, latitude: float, longitude: float, zone_type: str = "urban") -> ZoneSchema:
        zone_id = f"zone-{name.lower()}"
        if zone_id in self.zones:
            return None  # Zone déjà existe

        zone = ZoneSchema(
            id=zone_id,
            name=name,
            latitude=latitude,
            longitude=longitude,
            type=zone_type,
            createdAt=datetime.utcnow(),
        )
        self.zones[zone_id] = zone
        log.info("Zone créée : %s", zone_id)
        return zone

    def update_zone(self, zone_id: str, name: Optional[str] = None, latitude: Optional[float] = None, 
                    longitude: Optional[float] = None, zone_type: Optional[str] = None) -> Optional[ZoneSchema]:
        zone = self.zones.get(zone_id)
        if not zone:
            return None

        if name:
            zone.name = name
        if latitude is not None:
            zone.latitude = latitude
        if longitude is not None:
            zone.longitude = longitude
        if zone_type:
            zone.type = zone_type

        log.info("Zone modifiée : %s", zone_id)
        return zone

    def delete_zone(self, zone_id: str) -> bool:
        if zone_id in self.zones:
            del self.zones[zone_id]
            log.info("Zone supprimée : %s", zone_id)
            return True
        return False


class SensorController:
    def __init__(self, sensor_processor: SensorStreamProcessor):
        self.processor = sensor_processor

    def get_all_sensors(self) -> List[SensorSchema]:
        sensors = []
        for sid, sensor in self.processor.sensors.items():
            sensors.append(self._sensor_to_schema(sid, sensor))
        return sensors

    def get_sensor_by_id(self, sensor_id: str) -> Optional[SensorSchema]:
        sensor = self.processor.sensors.get(sensor_id)
        if not sensor:
            return None
        return self._sensor_to_schema(sensor_id, sensor)

    def get_sensors_by_zone(self, zone_id: str) -> List[SensorSchema]:
        zone_name = zone_id.replace("zone-", "").capitalize()
        return [
            self._sensor_to_schema(sid, s)
            for sid, s in self.processor.sensors.items()
            if zone_name.lower() in sid.lower()
        ]

    def get_sensors_by_status(self, status: str) -> List[SensorSchema]:
        try:
            sensor_status = SensorStatus[status.upper()]
        except KeyError:
            return []

        return [
            self._sensor_to_schema(sid, s)
            for sid, s in self.processor.sensors.items()
            if s.status == sensor_status
        ]

    def create_sensor(self, sensor_id: str, name: str, sensor_type: str, zone_id: str, 
                     latitude: float, longitude: float) -> Optional[SensorSchema]:
        if sensor_id in self.processor.sensors:
            return None  # Capteur déjà existe

        sensor = Sensor(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            latitude=latitude,
            longitude=longitude,
        )
        self.processor.sensors[sensor_id] = sensor
        log.info("Capteur créé : %s", sensor_id)
        return self._sensor_to_schema(sensor_id, sensor)

    def update_sensor(self, sensor_id: str, name: Optional[str] = None, sensor_type: Optional[str] = None,
                     latitude: Optional[float] = None, longitude: Optional[float] = None) -> Optional[SensorSchema]:
        sensor = self.processor.sensors.get(sensor_id)
        if not sensor:
            return None

        if latitude is not None:
            sensor.latitude = latitude
        if longitude is not None:
            sensor.longitude = longitude
        # Note: sensor_id et sensor_type ne sont pas modifiables

        log.info("Capteur modifié : %s", sensor_id)
        return self._sensor_to_schema(sensor_id, sensor)

    def delete_sensor(self, sensor_id: str) -> bool:
        if sensor_id in self.processor.sensors:
            del self.processor.sensors[sensor_id]
            log.info("Capteur supprimé : %s", sensor_id)
            return True
        return False

    @staticmethod
    def _sensor_to_schema(sensor_id: str, sensor: Sensor) -> SensorSchema:
        return SensorSchema(
            id=sensor_id,
            name=f"Capteur {sensor.sensor_type}",
            type=sensor.sensor_type,
            zoneId=f"zone-{sensor_id.split('_')[1].lower() if '_' in sensor_id else 'unknown'}",
            latitude=sensor.latitude or 0.0,
            longitude=sensor.longitude or 0.0,
            status=sensor.status.value,
            anomalyStreak=sensor.anomaly_streak,
            lastValue=sensor.last_value,
            lastUnit=sensor.last_unit,
            lastTimestamp=sensor.last_timestamp,
        )


class MetricController:
    def __init__(self, sensor_processor: SensorStreamProcessor):
        self.processor = sensor_processor
        self.metrics: Dict[str, MetricSchema] = {}

    def create_metric(self, metric_data: MetricCreateSchema) -> Optional[MetricSchema]:
        metric_id = f"metric-{uuid4().hex[:8]}"

        metric = MetricSchema(
            id=metric_id,
            sensorId=metric_data.sensorId,
            zoneId="unknown",
            type=metric_data.type,
            value=metric_data.value,
            unit=metric_data.unit,
            timestamp=metric_data.timestamp,
            isAnomaly=metric_data.isAnomaly,
        )

        self.metrics[metric_id] = metric
        log.info("Métrique créée : %s", metric_id)
        return metric

    def get_metric_by_id(self, metric_id: str) -> Optional[MetricSchema]:
        return self.metrics.get(metric_id)

    def get_metrics_by_sensor(self, sensor_id: str) -> List[MetricSchema]:
        return [m for m in self.metrics.values() if m.sensorId == sensor_id]

    def get_metrics_by_zone(self, zone_id: str) -> List[MetricSchema]:
        return [m for m in self.metrics.values() if m.zoneId == zone_id]

    def get_all_metrics(self, limit: int = 100) -> List[MetricSchema]:
        return list(self.metrics.values())[-limit:]
    
    def get_metrics(
        self,
        sensor_id: Optional[str] = None,
        zone_id: Optional[str] = None,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[MetricSchema]:
        metrics = list(self.metrics.values())

        if sensor_id:
            metrics = [m for m in metrics if m.sensorId == sensor_id]

        if zone_id:
            metrics = [m for m in metrics if m.zoneId == zone_id]

        if start_date:
            metrics = [m for m in metrics if m.timestamp >= start_date]

        if end_date:
            metrics = [m for m in metrics if m.timestamp <= end_date]

        return metrics[:limit]

    def delete_metric(self, metric_id: str) -> bool:
        if metric_id in self.metrics:
            del self.metrics[metric_id]
            log.info("Métrique supprimée : %s", metric_id)
            return True
        return False
    
    # Dans la classe MetricController
# ...existing code...

    def update_metric(self, metric_id: str, value: Optional[float] = None, 
                     unit: Optional[str] = None, isAnomaly: Optional[bool] = None) -> Optional[MetricSchema]:
        metric = self.metrics.get(metric_id)
        if not metric:
            return None

        if value is not None:
            metric.value = value
        if unit is not None:
            metric.unit = unit
        if isAnomaly is not None:
            metric.isAnomaly = isAnomaly

        log.info("Métrique modifiée : %s", metric_id)
        return metric

# ...existing code...