import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
import pika
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Gauge
from prometheus_fastapi_instrumentator import Instrumentator

from .config import RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS, RABBITMQ_PORT, RABBITMQ_QUEUE
from .exceptions import InvalidSensorIdError, MetricValidationError
from .schemas import SensorMetricIn, SensorMetricsResult
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.pika import PikaInstrumentor

resource = Resource(attributes={"service.name": "ingestion-service"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://tempo:4317", insecure=True))
)
trace.set_tracer_provider(provider)

PikaInstrumentor().instrument()
log = logging.getLogger("ingestion")
log.setLevel(logging.INFO)


# --- Logs JSON pour Logstash --------------------------------------------
# Écrits dans un fichier partagé (volume Docker) que Logstash tail via son
# input "file". Pas de dépendance supplémentaire : formatter JSON maison.
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


_LOG_DIR = os.getenv("LOG_DIR", "/var/log/app")
os.makedirs(_LOG_DIR, exist_ok=True)
_file_handler = logging.FileHandler(os.path.join(_LOG_DIR, "ingestion.jsonl"))
_file_handler.setFormatter(JsonFormatter())
log.addHandler(_file_handler)

_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
log.addHandler(_stream_handler)


app = FastAPI(
    title="Ingestion Service",
    description="Réception et transfert des métriques brutes.",
    version="1.0.0",
)
FastAPIInstrumentor.instrument_app(app)
# Golden Signals (Rate / Errors / Duration) : générés automatiquement par
# route, méthode et code de statut. Exposés sur /metrics.
Instrumentator().instrument(app).expose(app)


# --- Métriques métier UrbanHub ------------------------------------------
MEASUREMENTS_TOTAL = Counter(
    "urbanhub_measurements_total",
    "Nombre de mesures ingérées",
    ["sensor_type", "metric"],
)
ALERTS_TOTAL = Counter(
    "urbanhub_alerts_total",
    "Nombre d'alertes déclenchées (valeur hors seuil)",
    ["sensor_type", "metric"],
)
FRESHNESS_SECONDS = Gauge(
    "urbanhub_measurement_freshness_seconds",
    "Âge (secondes) de la dernière mesure reçue par type de capteur. "
    "Utiliser min_over_time()/max_over_time() en PromQL pour le panneau freshness.",
    ["sensor_type"],
)
MONTHLY_COST_EUROS = Gauge(
    "urbanhub_monthly_cost_euros",
    "Coût cumulé simulé du mois en cours (mock, pas une vraie facturation)",
)

# Seuils simples pour détecter une alerte (cohérent avec le simulateur qui
# injecte des PM2.5 > 75 pour tester la chaîne d'alerte).
ALERT_THRESHOLDS = {"pm25": 75.0}

# Coût simulé : X€ par mesure ingérée, cumulé depuis le démarrage du service
# (mock volontairement simple — pas de vraie source de facturation).
_COST_PER_MEASUREMENT_EUR = 0.0002
_monthly_cost_lock = threading.Lock()
_monthly_cost = 0.0


def _sensor_type_from_id(sensor_id: str) -> str:
    prefix = sensor_id.split("-")[0].upper()
    return {"TRAF": "traffic", "AIR": "air"}.get(prefix, "unknown")


def _record_business_metrics(sensor_id: str, m: SensorMetricIn) -> None:
    global _monthly_cost
    sensor_type = _sensor_type_from_id(sensor_id)

    MEASUREMENTS_TOTAL.labels(sensor_type=sensor_type, metric=m.metric).inc()

    threshold = ALERT_THRESHOLDS.get(m.metric)
    if threshold is not None and m.value > threshold:
        ALERTS_TOTAL.labels(sensor_type=sensor_type, metric=m.metric).inc()
        log.warning(
            f"Alerte déclenchée : {m.metric}={m.value} > {threshold} "
            f"(sensor_id={sensor_id})"
        )

    try:
        recorded_dt = datetime.fromisoformat(m.recorded_at.replace("Z", "+00:00"))
        age_seconds = (datetime.now(timezone.utc) - recorded_dt).total_seconds()
        FRESHNESS_SECONDS.labels(sensor_type=sensor_type).set(max(age_seconds, 0))
    except (ValueError, AttributeError):
        log.warning(f"recorded_at invalide, freshness non calculée : {m.recorded_at!r}")

    with _monthly_cost_lock:
        _monthly_cost += _COST_PER_MEASUREMENT_EUR
        MONTHLY_COST_EUROS.set(_monthly_cost)


# --- Connexion RabbitMQ partagée ---------------------------------------
# pika.BlockingConnection n'est pas thread-safe : uvicorn exécute les
# endpoints "def" (non-async) dans un threadpool, donc on protège tout
# accès au channel avec un verrou.
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

    # 4. Publication vers RabbitMQ + métriques métier
    for m in metrics:
        _publish({
            "sensor_external_id": sensor_id,
            "metric": m.metric,
            "value": m.value,
            "unit": m.unit,
            "recorded_at": m.recorded_at,
        })
        _record_business_metrics(sensor_id, m)

    return SensorMetricsResult(status="accepted", processed_count=len(metrics))