import json
import logging
import threading

import pika
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from .config import RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS, RABBITMQ_PORT, RABBITMQ_QUEUE
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

# --- Connexion RabbitMQ partagée ---------------------------------------
_rabbit_lock = threading.Lock()
_connection: pika.BlockingConnection | None = None
_channel = None


def _connect_rabbitmq(retries: int = 30) -> None:
    global _connection, _channel
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300,
    )

    for i in range(retries):
        try:
            _connection = pika.BlockingConnection(parameters)
            _channel = _connection.channel()
            _channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            log.info(f"Connecté à RabbitMQ sur {RABBITMQ_HOST}:{RABBITMQ_PORT}")
            return
        except pika.exceptions.AMQPConnectionError:
            log.warning(f"RabbitMQ pas prêt (essai {i + 1}/{retries}), retry dans 3s…")
            import time
            time.sleep(3)

    raise RuntimeError("RabbitMQ indisponible après retries")


def _publish(message: dict) -> None:
    """Publie un message, en se reconnectant automatiquement si besoin."""
    global _connection, _channel
    with _rabbit_lock:
        try:
            _channel.basic_publish(
                exchange="",
                routing_key=RABBITMQ_QUEUE,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # message persistant
                    content_type="application/json",
                ),
            )
        except pika.exceptions.AMQPError as e:
            log.warning(f"Erreur d'envoi RabbitMQ : {e}, reconnexion…")
            _connect_rabbitmq()
            _channel.basic_publish(
                exchange="",
                routing_key=RABBITMQ_QUEUE,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                ),
            )


@app.on_event("startup")
def on_startup():
    _connect_rabbitmq()


@app.on_event("shutdown")
def on_shutdown():
    if _connection and _connection.is_open:
        _connection.close()


# --- Gestion des erreurs -------------------------------------------------
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
    # 1. Rejeter un ID de capteur vide
    if not sensor_id or not sensor_id.strip():
        raise InvalidSensorIdError("sensor_id ne peut pas être vide")

    # 2. Rejeter une liste de métriques vide
    if not metrics:
        raise MetricValidationError("La liste de métriques ne peut pas être vide")

    # 3. Rejeter toute métrique dont un champ obligatoire est vide/nul
    for m in metrics:
        if not m.metric or not m.metric.strip():
            raise MetricValidationError("Le champ 'metric' ne peut pas être vide")
        if m.value is None:
            raise MetricValidationError("Le champ 'value' ne peut pas être vide")
        if not m.unit or not m.unit.strip():
            raise MetricValidationError("Le champ 'unit' ne peut pas être vide")
        if not m.recorded_at:
            raise MetricValidationError("Le champ 'recorded_at' ne peut pas être vide")

    log.info(f"Reçu {len(metrics)} métriques pour le capteur {sensor_id}")

    # 4. Publication vers RabbitMQ pour le validation-service
    for m in metrics:
        _publish({
            "sensor_external_id": sensor_id,
            "metric": m.metric,
            "value": m.value,
            "unit": m.unit,
            "recorded_at": m.recorded_at,
        })

    return SensorMetricsResult(status="accepted", processed_count=len(metrics))