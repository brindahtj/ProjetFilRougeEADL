import logging
import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from .exceptions import InvalidSensorIdError, MetricValidationError
from .schemas import SensorMetricIn, SensorMetricsResult

VALIDATION_SERVICE_URL = os.getenv(
    "VALIDATION_SERVICE_URL",
    "http://validation:8002"
)

SENSOR_META = {
    "AIR-001": {
        "city": "paris",
        "zone": "nord",
        "latitude": 48.89,
        "longitude": 2.35,
    },
    "AIR-002": {
        "city": "paris",
        "zone": "sud",
        "latitude": 48.82,
        "longitude": 2.35,
    },
    "AIR-003": {
        "city": "paris",
        "zone": "centre",
        "latitude": 48.8566,
        "longitude": 2.3522,
    },
    "TRAF-001": {
        "city": "paris",
        "zone": "nord",
        "latitude": 48.89,
        "longitude": 2.35,
        "street": "Rue Nord",
        "section_id": "N-001",
    },
    "TRAF-002": {
        "city": "paris",
        "zone": "sud",
        "latitude": 48.82,
        "longitude": 2.35,
        "street": "Rue Sud",
        "section_id": "S-001",
    },
    "TRAF-003": {
        "city": "paris",
        "zone": "centre",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "street": "Rue Centre",
        "section_id": "C-001",
    },
}

log = logging.getLogger("ingestion")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Ingestion Service",
    description="Réception et transfert des métriques brutes.",
    version="1.0.0",
)

Instrumentator().instrument(app).expose(app)

@app.exception_handler(InvalidSensorIdError)
def handle_invalid_sensor_id(request: Request, exc: InvalidSensorIdError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.exception_handler(MetricValidationError)
def handle_metric_validation_error(request: Request, exc: MetricValidationError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "ingestion-service"}

@app.post(
    "/api/v1/sensors/{sensor_id}/metrics",
    response_model=SensorMetricsResult,
    status_code=202,
    tags=["Sensors"],
)
def post_sensor_metrics(sensor_id: str, metrics: list[SensorMetricIn]):

    log.info(f"Reçu {len(metrics)} métriques pour le capteur {sensor_id}")

    sensor = SENSOR_META.get(sensor_id)

    if not sensor:
        raise InvalidSensorIdError(f"Capteur inconnu : {sensor_id}")

    processed = 0

    for metric in metrics:

        payload = None

        # AIR -> pollution
        if sensor_id.startswith("AIR-"):

            if metric.metric not in {"pm25", "no2"}:
                log.info(
                    "Métrique ignorée pour validation : %s",
                    metric.metric
                )
                continue

            payload = {
                "type": "pollution",
                "city": sensor["city"],
                "zone": sensor["zone"],
                "pollutant": metric.metric,
                "value": metric.value,
                "latitude": sensor["latitude"],
                "longitude": sensor["longitude"],
                "timestamp": metric.recorded_at,
            }

        # TRAF -> traffic
        elif sensor_id.startswith("TRAF-"):

            if metric.metric != "vehicles_per_min":
                log.info(
                    "Métrique ignorée pour validation : %s",
                    metric.metric
                )
                continue

            payload = {
                "type": "traffic",
                "city": sensor["city"],
                "zone": sensor["zone"],
                "street": sensor["street"],
                "section_id": sensor["section_id"],
                "q": metric.value * 60,
                "latitude": sensor["latitude"],
                "longitude": sensor["longitude"],
                "timestamp": metric.recorded_at,
            }

        if payload:
            response = requests.post(
                f"{VALIDATION_SERVICE_URL}/validate",
                params={"sensor_id": sensor_id},
                json=payload,
                timeout=5,
            )

            log.info(
                "Validation %s → %s",
                sensor_id,
                response.status_code,
            )

            if response.status_code == 200:
                processed += 1

    return SensorMetricsResult(
        status="accepted",
        processed_count=processed,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)