import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from .exceptions import InvalidSensorIdError, MetricValidationError
from .schemas import SensorMetricIn, SensorMetricsResult

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
    tags=["Sensors"]
)
def post_sensor_metrics(sensor_id: str, metrics: list[SensorMetricIn]):
    log.info(f"Reçu {len(metrics)} métriques pour le capteur {sensor_id}")
    return SensorMetricsResult(status="accepted", processed_count=len(metrics))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)