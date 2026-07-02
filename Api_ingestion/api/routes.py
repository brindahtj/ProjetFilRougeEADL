import logging
from typing import Dict, Any, Optional
from datetime import datetime

from Api_ingestion.api.controllers import ZoneController, SensorController, MetricController
from Api_ingestion.api.schemas import MetricCreateSchema
from Api_ingestion.sensor_processor import SensorStreamProcessor

log = logging.getLogger(__name__)


class APIRouter:
    def __init__(self, sensor_processor: SensorStreamProcessor):
        self.zone_controller = ZoneController()
        self.sensor_controller = SensorController(sensor_processor)
        self.metric_controller = MetricController(sensor_processor)

    # ===== ZONES =====

    def get_zones(self) -> Dict[str, Any]:
        """GET /api/v1/zones"""
        try:
            zones = self.zone_controller.get_all_zones()
            return {
                "status": 200,
                "data": [z.__dict__ for z in zones],
                "message": f"{len(zones)} zones trouvées"
            }
        except Exception as e:
            log.error("Erreur GET /zones : %s", e)
            return {"status": 500, "error": str(e)}

    def get_zone(self, zone_id: str) -> Dict[str, Any]:
        """GET /api/v1/zones/{zoneId}"""
        zone = self.zone_controller.get_zone_by_id(zone_id)
        if not zone:
            return {"status": 404, "error": f"Zone {zone_id} non trouvée"}
        return {"status": 200, "data": zone.__dict__}

    def create_zone(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /api/v1/zones"""
        try:
            name = payload.get("name")
            latitude = payload.get("latitude")
            longitude = payload.get("longitude")
            zone_type = payload.get("type", "urban")

            if not all([name, latitude is not None, longitude is not None]):
                return {"status": 400, "error": "Champs manquants : name, latitude, longitude"}

            zone = self.zone_controller.create_zone(name, float(latitude), float(longitude), zone_type)
            if not zone:
                return {"status": 409, "error": f"Zone {name} existe déjà"}

            return {"status": 201, "data": zone.__dict__, "message": "Zone créée"}
        except Exception as e:
            log.error("Erreur POST /zones : %s", e)
            return {"status": 500, "error": str(e)}

    def update_zone(self, zone_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """PUT /api/v1/zones/{zoneId}"""
        try:
            zone = self.zone_controller.update_zone(
                zone_id,
                name=payload.get("name"),
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude"),
                zone_type=payload.get("type"),
            )
            if not zone:
                return {"status": 404, "error": f"Zone {zone_id} non trouvée"}

            return {"status": 200, "data": zone.__dict__, "message": "Zone modifiée"}
        except Exception as e:
            log.error("Erreur PUT /zones/{zoneId} : %s", e)
            return {"status": 500, "error": str(e)}

    def delete_zone(self, zone_id: str) -> Dict[str, Any]:
        """DELETE /api/v1/zones/{zoneId}"""
        try:
            if self.zone_controller.delete_zone(zone_id):
                return {"status": 200, "message": f"Zone {zone_id} supprimée"}
            return {"status": 404, "error": f"Zone {zone_id} non trouvée"}
        except Exception as e:
            log.error("Erreur DELETE /zones/{zoneId} : %s", e)
            return {"status": 500, "error": str(e)}

    # ===== SENSORS =====

    def get_sensors(self, zone_id: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """GET /api/v1/sensors?zoneId=...&status=..."""
        try:
            if zone_id:
                sensors = self.sensor_controller.get_sensors_by_zone(zone_id)
            elif status:
                sensors = self.sensor_controller.get_sensors_by_status(status)
            else:
                sensors = self.sensor_controller.get_all_sensors()

            return {
                "status": 200,
                "data": [s.__dict__ for s in sensors],
                "message": f"{len(sensors)} capteurs trouvés"
            }
        except Exception as e:
            log.error("Erreur GET /sensors : %s", e)
            return {"status": 500, "error": str(e)}
        
    def get_sensor(self, sensor_id: str) -> Dict[str, Any]:
        sensor = self.sensor_controller.get_sensor_by_id(sensor_id)

        if not sensor:
            return {
                "status": 404,
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Capteur {sensor_id} non trouvé",
                    "resource": f"/api/v1/sensors/{sensor_id}",
                },
            }
        
        domain_sensor = self.sensor_controller.processor.sensors.get(sensor_id)

        if getattr(domain_sensor, "is_online", True) is False:
            return {
                "status": 503,
                "error": {
                    "code": "SENSOR_OFFLINE",
                    "message": "Le capteur est actuellement hors ligne",
                    "resource": f"/api/v1/sensors/{sensor_id}",
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "details": {
                        "sensorId": sensor_id,
                        "sensorType": sensor.type,
                        "lastSeen": getattr(domain_sensor, "last_seen", None),
                        "offlineSince": getattr(domain_sensor, "offline_since", None),
                    },
                    "retryable": True,
                    "retryAfterSeconds": 60,
                },
        }

        return {
        "status": 200,
        "data": sensor.__dict__,
    }

    def create_sensor(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /api/v1/sensors"""
        try:
            sensor_id = payload.get("id")
            name = payload.get("name")
            sensor_type = payload.get("type")
            zone_id = payload.get("zoneId")
            latitude = payload.get("latitude")
            longitude = payload.get("longitude")

            if not all([sensor_id, name, sensor_type, zone_id, latitude is not None, longitude is not None]):
                return {"status": 400, "error": "Champs manquants"}

            sensor = self.sensor_controller.create_sensor(
                sensor_id, name, sensor_type, zone_id, float(latitude), float(longitude)
            )
            if not sensor:
                return {"status": 409, "error": f"Capteur {sensor_id} existe déjà"}

            return {"status": 201, "data": sensor.__dict__, "message": "Capteur créé"}
        except Exception as e:
            log.error("Erreur POST /sensors : %s", e)
            return {"status": 500, "error": str(e)}

    def update_sensor(self, sensor_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """PUT /api/v1/sensors/{sensorId}"""
        try:
            sensor = self.sensor_controller.update_sensor(
                sensor_id,
                name=payload.get("name"),
                sensor_type=payload.get("type"),
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude"),
            )
            if not sensor:
                return {"status": 404, "error": f"Capteur {sensor_id} non trouvé"}

            return {"status": 200, "data": sensor.__dict__, "message": "Capteur modifié"}
        except Exception as e:
            log.error("Erreur PUT /sensors/{sensorId} : %s", e)
            return {"status": 500, "error": str(e)}

    def delete_sensor(self, sensor_id: str) -> Dict[str, Any]:
        """DELETE /api/v1/sensors/{sensorId}"""
        try:
            if self.sensor_controller.delete_sensor(sensor_id):
                return {"status": 200, "message": f"Capteur {sensor_id} supprimé"}
            return {"status": 404, "error": f"Capteur {sensor_id} non trouvé"}
        except Exception as e:
            log.error("Erreur DELETE /sensors/{sensorId} : %s", e)
            return {"status": 500, "error": str(e)}

    # ===== METRICS =====
    def parse_date(value: Optional[str]) -> Optional[datetime]:
        """Convertit une chaîne ISO en datetime."""
        if value is None:
            return None
        return datetime.fromisoformat(value)
    
    def get_metrics(
            self,
            sensor_id: Optional[str] = None,
            zone_id: Optional[str] = None,
            limit: int = 100,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """GET /api/v1/metrics?sensorId=...&zoneId=...&limit=...&start_date=...&end_date=..."""
        try:
            metrics = self.metric_controller.get_metrics(
                sensor_id=sensor_id,
                zone_id=zone_id,
                limit=limit,
                start_date=self.parse_date(start_date),
                end_date=self.parse_date(end_date),
            )

            return {
            "status": 200,
            "data": [m.__dict__ for m in metrics],
            "message": f"{len(metrics)} métriques trouvées",
            }
        except ValueError:
            return {
                "status": 400,
                "error": {
                    "code": "INVALID_DATE_FORMAT",
                    "message": "Format attendu : YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS",
                },
            }

        except Exception as e:
            return {"status": 500, "error": str(e)}

    def get_metric(self, metric_id: str) -> Dict[str, Any]:
        """GET /api/v1/metrics/{metricId}"""
        metric = self.metric_controller.get_metric_by_id(metric_id)
        if not metric:
            return {"status": 404, "error": f"Métrique {metric_id} non trouvée"}
        return {"status": 200, "data": metric.__dict__}

    def create_metric(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /api/v1/metrics"""
        try:
            metric_data = MetricCreateSchema(
                sensorId=payload["sensorId"],
                type=payload["type"],
                value=float(payload["value"]),
                unit=payload["unit"],
                timestamp=payload.get("timestamp") or datetime.utcnow(),
                isAnomaly=payload.get("isAnomaly", False),
            )
            metric = self.metric_controller.create_metric(metric_data)
            return {
                "status": 201,
                "data": metric.__dict__,
                "message": "Métrique créée avec succès"
            }
        except KeyError as e:
            return {"status": 400, "error": f"Champ manquant : {e}"}
        except Exception as e:
            log.error("Erreur POST /metrics : %s", e)
            return {"status": 500, "error": str(e)}

    def delete_metric(self, metric_id: str) -> Dict[str, Any]:
        """DELETE /api/v1/metrics/{metricId}"""
        try:
            if self.metric_controller.delete_metric(metric_id):
                return {"status": 200, "message": f"Métrique {metric_id} supprimée"}
            return {"status": 404, "error": f"Métrique {metric_id} non trouvée"}
        except Exception as e:
            log.error("Erreur DELETE /metrics/{metricId} : %s", e)
            return {"status": 500, "error": str(e)}
    
      # ===== UPDATE METRICS =====

    def update_metric(self, metric_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """PUT /api/v1/metrics/{metricId}"""
        try:
            metric = self.metric_controller.update_metric(
                metric_id,
                value=payload.get("value"),
                unit=payload.get("unit"),
                isAnomaly=payload.get("isAnomaly"),
            )
            if not metric:
                return {"status": 404, "error": f"Métrique {metric_id} non trouvée"}

            return {"status": 200, "data": metric.__dict__, "message": "Métrique modifiée"}
        except Exception as e:
            log.error("Erreur PUT /metrics/{metricId} : %s", e)
            return {"status": 500, "error": str(e)}

# ...existing code...


# Instance globale du routeur
router: Optional[APIRouter] = None


def init_router(sensor_processor: SensorStreamProcessor) -> APIRouter:
    global router
    router = APIRouter(sensor_processor)
    return router