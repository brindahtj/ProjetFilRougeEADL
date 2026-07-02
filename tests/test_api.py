import json
import unittest
from datetime import datetime
from pathlib import Path

from Api_ingestion.api.routes import init_router
from Api_ingestion.domain import Sensor, SensorStatus
from Api_ingestion.sensor_processor import SensorStreamProcessor

EXAMPLES_PATH = Path(__file__).resolve().parents[1] / "docs" / "api" / "examples.json"

with EXAMPLES_PATH.open(encoding="utf-8") as f:
    EXAMPLES = json.load(f)


class TestZonesAPI(unittest.TestCase):
    def setUp(self):
        self.processor = SensorStreamProcessor()
        self.router = init_router(self.processor)

    def test_get_zones_returns_200(self):
        response = self.router.get_zones()
        self.assertEqual(response["status"], 200)
        self.assertIn("data", response)

    def test_get_zone_by_id_returns_200(self):
        response = self.router.get_zone("zone-paris")
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["data"]["id"], "zone-paris")

    def test_get_zone_not_found_returns_404(self):
        response = self.router.get_zone("zone-inconnu")
        self.assertEqual(response["status"], 404)

    def test_create_zone_returns_201(self):
        payload = EXAMPLES["zone_create_payload"]
        response = self.router.create_zone(payload)
        self.assertEqual(response["status"], 201)
        self.assertEqual(response["data"]["name"], payload["name"])

    def test_update_zone_returns_200(self):
        self.router.create_zone(EXAMPLES["zone_create_payload"])
        response = self.router.update_zone("zone-paris", {"name": "Paris Updated"})
        self.assertEqual(response["status"], 200)
        self.assertIn("Paris", response["data"]["name"])

    def test_delete_zone_returns_200(self):
        self.router.create_zone({
            "name": "TempZone",
            "latitude": 0.0,
            "longitude": 0.0,
            "type": "urban"
        })
        response = self.router.delete_zone("zone-tempzone")
        self.assertEqual(response["status"], 200)


class TestSensorsAPI(unittest.TestCase):
    def setUp(self):
        self.processor = SensorStreamProcessor()
        self.router = init_router(self.processor)

    def test_get_sensors_returns_200(self):
        response = self.router.get_sensors()
        self.assertEqual(response["status"], 200)

    def test_get_sensor_by_id_returns_200(self):
        payload = EXAMPLES["sensor_create_payload"]
        self.router.create_sensor(payload)
        response = self.router.get_sensor(payload["id"])
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["data"]["id"], payload["id"])

    def test_get_sensor_not_found_returns_404(self):
        response = self.router.get_sensor("sensor-inconnu")
        self.assertEqual(response["status"], 404)

    def test_create_sensor_returns_201(self):
        payload = EXAMPLES["sensor_create_payload"]
        response = self.router.create_sensor(payload)
        self.assertEqual(response["status"], 201)
        self.assertEqual(response["data"]["id"], payload["id"])

    def test_update_sensor_returns_200(self):
        payload = EXAMPLES["sensor_create_payload"]
        self.router.create_sensor(payload)
        response = self.router.update_sensor(payload["id"], {"latitude": 49.0, "longitude": 3.0})
        self.assertEqual(response["status"], 200)

    def test_delete_sensor_returns_200(self):
        payload = EXAMPLES["sensor_create_payload"]
        self.router.create_sensor(payload)
        response = self.router.delete_sensor(payload["id"])
        self.assertEqual(response["status"], 200)


class TestMetricsAPI(unittest.TestCase):
    def setUp(self):
        self.processor = SensorStreamProcessor()
        self.router = init_router(self.processor)

    def test_get_metrics_returns_200(self):
        response = self.router.get_metrics()
        self.assertEqual(response["status"], 200)

    def test_create_metric_returns_201(self):
        payload = EXAMPLES["metric_create_payload"]
        response = self.router.create_metric(payload)
        self.assertEqual(response["status"], 201)
        self.assertEqual(response["data"]["sensorId"], payload["sensorId"])

    def test_get_metric_by_id_returns_200(self):
        payload = EXAMPLES["metric_create_payload"]
        create_response = self.router.create_metric(payload)
        metric_id = create_response["data"]["id"]
        response = self.router.get_metric(metric_id)
        self.assertEqual(response["status"], 200)

    def test_get_metric_not_found_returns_404(self):
        response = self.router.get_metric("metric-inconnu")
        self.assertEqual(response["status"], 404)

    def test_create_metric_missing_field_returns_400(self):
        payload = {
            "sensorId": "sensor-pollution-001",
            "type": "pollution",
            "unit": "µg/m³"
        }
        response = self.router.create_metric(payload)
        self.assertEqual(response["status"], 400)

    def test_delete_metric_returns_200(self):
        payload = EXAMPLES["metric_create_payload"]
        create_response = self.router.create_metric(payload)
        metric_id = create_response["data"]["id"]
        response = self.router.delete_metric(metric_id)
        self.assertEqual(response["status"], 200)


class TestSensorStateTransition(unittest.TestCase):
    def test_sensor_state_normal(self):
        sensor = Sensor("s1", "pollution")
        sensor.update(value=10.0, unit="µg/m³", timestamp=datetime.utcnow(), is_anomaly=False)
        self.assertEqual(sensor.status, SensorStatus.NORMAL)

    def test_sensor_state_warning(self):
        sensor = Sensor("s1", "pollution")
        sensor.update(value=10.0, unit="µg/m³", timestamp=datetime.utcnow(), is_anomaly=True)
        self.assertEqual(sensor.status, SensorStatus.WARNING)

    def test_sensor_state_critical(self):
        sensor = Sensor("s1", "pollution")
        sensor.update(value=10.0, unit="µg/m³", timestamp=datetime.utcnow(), is_anomaly=True)
        sensor.update(value=11.0, unit="µg/m³", timestamp=datetime.utcnow(), is_anomaly=True)
        sensor.update(value=12.0, unit="µg/m³", timestamp=datetime.utcnow(), is_anomaly=True)
        self.assertEqual(sensor.status, SensorStatus.CRITICAL)


if __name__ == "__main__":
    unittest.main()