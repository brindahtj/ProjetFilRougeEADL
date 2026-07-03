import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import VALIDATION_SERVICE_URL
from .exceptions import InvalidSensorIdError, MetricValidationError
from .schemas import SensorMetricIn, SensorMetricsResult
from .sensor_stream_processor import SensorStreamProcessor

log = logging.getLogger("ingestion")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Ingestion Service",
    description="Réception des flux de métriques capteurs et suivi de leur état de santé.",
    version="1.0.0",
)

_processor = SensorStreamProcessor(validation_service_url=VALIDATION_SERVICE_URL)


@app.exception_handler(InvalidSensorIdError)
def handle_invalid_sensor_id(request: Request, exc: InvalidSensorIdError) -> JSONResponse:
    """Identifiant de capteur malformé → 400 Bad Request."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(MetricValidationError)
def handle_metric_validation_error(request: Request, exc: MetricValidationError) -> JSONResponse:
    """Flux de métriques sémantiquement invalide → 422 Unprocessable Entity."""
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/health", tags=["Health"], summary="Vérifier la santé du service")
def health():
    return {"status": "ok", "service": "ingestion-service"}


@app.post(
    "/api/v1/sensors/{sensor_id}/metrics",
    response_model=SensorMetricsResult,
    status_code=202,
    tags=["Sensors"],
    summary="Envoyer un lot de métriques pour un capteur",
    description="""
    Reçoit un lot de métriques brutes émises par un capteur, les transmet à
    `validation-service` (qui connaît déjà `sensor_id` via cette route), et
    met à jour l'état du capteur en fonction du verdict reçu.

    - `sensor_id` malformé → **400**
    - lot de métriques vide → **422**
    - métrique jugée **incomplète** par `validation-service` (champ requis
      manquant) → rejetée, sans impact sur l'état du capteur.
    - métrique jugée **aberrante** par `validation-service` (valeur hors
      plage physiquement plausible) → non publiée, mais fait transitionner
      l'état du capteur (`sensor_status`, pattern State NORMAL → WARNING →
      CRITICAL).
    - métrique **valide** (même élevée mais plausible) → publiée par
      `validation-service`, état du capteur ramené vers NORMAL.
    """,
)
def post_sensor_metrics(sensor_id: str, metrics: list[SensorMetricIn]) -> SensorMetricsResult:
    result = _processor.process(sensor_id, metrics)
    return SensorMetricsResult(**result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
