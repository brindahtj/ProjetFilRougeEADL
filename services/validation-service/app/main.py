import logging
import json
import threading
import time
from contextlib import asynccontextmanager

import pika
from fastapi import FastAPI, HTTPException

from .models import (
    RawMeasurement,
    ValidationResponse,
    BatchValidationResponse,
    HealthResponse,
)
from .validator import MeasurementValidator
from .config import (
    RABBITMQ_HOST,
    RABBITMQ_USER,
    RABBITMQ_PORT,
    RABBITMQ_PASS,
    RABBITMQ_QUEUE,  # queue où ingestion-service publie les mesures brutes
    EXCHANGE,
    API_TITLE,
    API_DESCRIPTION,
    API_VERSION,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

PREFETCH_COUNT = 10  # nb de messages non-ack en parallèle max côté consumer

# ─────────────────────────────────────────────────────────────────────────────
# RABBITMQ — PUBLISHER (vers EXCHANGE, pour association-service)
# ─────────────────────────────────────────────────────────────────────────────
_publisher_lock = threading.Lock()
publisher_connection: pika.BlockingConnection | None = None
publisher_channel = None


def init_rabbit(retries: int = 30, delay: int = 3) -> None:
    """Initialise la connexion RabbitMQ, avec retry pattern.

    RabbitMQ peut mettre 60-100s à démarrer complètement. Sans retry,
    un léger décalage entre "healthy" (docker) et "port réellement
    accepté" fait planter le lifespan de FastAPI au premier essai,
    d'où le ConnectionRefusedError observé.
    """
    global publisher_connection, publisher_channel
    creds = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=creds,
        heartbeat=600,
        blocked_connection_timeout=300,
    )

    for i in range(retries):
        try:
            publisher_connection = pika.BlockingConnection(params)
            publisher_channel = publisher_connection.channel()
            publisher_channel.exchange_declare(
                exchange=EXCHANGE, exchange_type="direct", durable=True
            )
            log.info("✓ RabbitMQ initialized")
            return
        except (pika.exceptions.AMQPConnectionError, ConnectionError) as e:
            log.warning(
                "RabbitMQ pas prêt (essai %d/%d), retry dans %ds… (%s)",
                i + 1, retries, delay, e,
            )
            time.sleep(delay)

    log.error("✗ RabbitMQ initialization failed after %d retries", retries)
    raise RuntimeError("RabbitMQ indisponible après retries")


def _publish_measurement(measurement: RawMeasurement) -> None:
    """Publie une mesure sur RabbitMQ.

    FastAPI exécute les routes sync dans un threadpool : plusieurs threads
    peuvent appeler cette fonction en même temps. pika.BlockingConnection
    n'est pas thread-safe, d'où le lock. On tente aussi une reconnexion
    automatique si le canal/la connexion est tombé.
    """
    global publisher_connection, publisher_channel
    routing_key = measurement.type
    body = json.dumps(measurement.dict(), default=str)

    with _publisher_lock:
        try:
            publisher_channel.basic_publish(
                exchange=EXCHANGE,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                ),
            )
        except (pika.exceptions.AMQPError, AttributeError) as e:
            log.warning("Erreur de publication RabbitMQ (%s), reconnexion…", e)
            init_rabbit()
            publisher_channel.basic_publish(
                exchange=EXCHANGE,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                ),
            )

    log.info("✓ Published to %s: %s", routing_key, measurement.city)


# ─────────────────────────────────────────────────────────────────────────────
# RABBITMQ — CONSUMER (depuis RABBITMQ_QUEUE, alimentée par ingestion-service)
# ─────────────────────────────────────────────────────────────────────────────
_consumer_connection: pika.BlockingConnection | None = None
_consumer_channel = None
_consumer_thread: threading.Thread | None = None
_should_stop = threading.Event()


def _connect_consumer(retries: int = 30, delay: int = 3) -> None:
    global _consumer_connection, _consumer_channel
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
            _consumer_connection = pika.BlockingConnection(parameters)
            _consumer_channel = _consumer_connection.channel()
            _consumer_channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            _consumer_channel.basic_qos(prefetch_count=PREFETCH_COUNT)
            log.info(
                "✓ Consumer connecté à RabbitMQ sur %s:%s (queue=%s)",
                RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_QUEUE,
            )
            return
        except pika.exceptions.AMQPConnectionError as e:
            log.warning(
                "RabbitMQ pas prêt (essai %d/%d), retry dans %ds… (%s)",
                i + 1, retries, delay, e,
            )
            time.sleep(delay)

    raise RuntimeError("RabbitMQ indisponible après retries (consumer)")


def _handle_raw_measurement(body: bytes) -> bool:
    """
    Parse + valide une mesure brute reçue d'ingestion-service.
    Publie sur EXCHANGE uniquement si NORMAL.
    Retourne True si le message doit être ack, False sinon.
    """
    try:
        payload = json.loads(body)
        sensor_id = payload.pop("sensor_id", None)
        measurement = RawMeasurement(**payload)
    except Exception as e:
        log.exception("Message illisible / invalide, rejeté sans requeue : %s", e)
        return True  # message malformé : on l'ack pour ne pas boucler dessus

    try:
        result = MeasurementValidator.validate(measurement, sensor_id=sensor_id)
    except Exception as e:
        log.exception("Erreur pendant la validation : %s", e)
        return False  # erreur transitoire potentielle -> on retente (nack requeue)

    if result.state == "NORMAL" and result.measurement:
        _publish_measurement(result.measurement)
        log.info(
            "✓ [NORMAL] %s / %s -> republié sur %s",
            result.measurement.type, result.measurement.city, EXCHANGE,
        )
    else:
        log.warning("✗ [CRITICAL] Mesure rejetée : %s", result.errors)

    return True


def _on_message(channel, method, properties, body):
    try:
        should_ack = _handle_raw_measurement(body)
    except Exception:
        log.exception("Erreur inattendue dans le traitement du message")
        should_ack = False

    if should_ack:
        channel.basic_ack(delivery_tag=method.delivery_tag)
    else:
        # requeue=False pour éviter les boucles infinies sur un message toxique
        # (idéalement une dead-letter queue configurée sur RABBITMQ_QUEUE)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def _consume_loop() -> None:
    global _consumer_connection, _consumer_channel

    while not _should_stop.is_set():
        try:
            if _consumer_connection is None or _consumer_connection.is_closed:
                _connect_consumer()

            _consumer_channel.basic_consume(
                queue=RABBITMQ_QUEUE,
                on_message_callback=_on_message,
                auto_ack=False,
            )
            log.info("Démarrage de la consommation RabbitMQ (%s)…", RABBITMQ_QUEUE)
            _consumer_channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            log.warning("Connexion RabbitMQ (consumer) perdue : %s, reconnexion…", e)
            time.sleep(3)
        except Exception as e:
            if not _should_stop.is_set():
                log.exception("Erreur inattendue dans la boucle consumer : %s", e)
                time.sleep(3)


def start_consumer() -> None:
    global _consumer_thread
    _should_stop.clear()
    _consumer_thread = threading.Thread(target=_consume_loop, daemon=True)
    _consumer_thread.start()


def stop_consumer() -> None:
    _should_stop.set()
    if _consumer_channel is not None and _consumer_channel.is_open:
        try:
            _consumer_channel.stop_consuming()
        except Exception:
            pass
    if _consumer_connection is not None and _consumer_connection.is_open:
        _consumer_connection.close()
    if _consumer_thread is not None:
        _consumer_thread.join(timeout=5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_rabbit()       # connexion publisher (-> EXCHANGE, association-service)
    start_consumer()    # connexion consumer (<- RABBITMQ_QUEUE, ingestion-service)
    yield
    # Shutdown
    stop_consumer()
    if publisher_connection and publisher_connection.is_open:
        publisher_connection.close()
        log.info("RabbitMQ connection closed")


# Configuration Swagger/OpenAPI
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    contact={"name": "Smart City Team", "email": "team@smartcity.local"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES DE SANTÉ
# ─────────────────────────────────────────────────────────────────────────────
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Vérifier la santé du service",
    description="Endpoint de santé pour les health checks",
)
def health():
    """Retourne le statut du service."""
    return HealthResponse(status="ok")


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES DE VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
@app.post(
    "/validate",
    response_model=ValidationResponse,
    tags=["Validation"],
    summary="Valider une mesure unique",
    description="""
    Valide une mesure brute (pollution ou trafic).
    ### États possibles
    - **NORMAL** : donnée complète et conforme → publication sur RabbitMQ
    - **CRITICAL** : donnée incomplète ou aberrante → rejet et mise de côté
    ### Validations effectuées
    - Type de mesure (pollution ou traffic)
    - Champs obligatoires (city, latitude, longitude, timestamp)
    - Plages de valeurs (latitude, longitude, valeur, q)
    - Cohérence du timestamp (pas plus de 5 min dans le futur, pas plus de 24h dans le passé)
    - Contraintes spécifiques au type (pollutant, value pour pollution ; street, section_id, q pour traffic)
    """,
    responses={
        200: {
            "description": "Validation réussie",
            "content": {
                "application/json": {
                    "example": {
                        "state": "NORMAL",
                        "valid": True,
                        "message": "Measurement published to event bus",
                        "routing_key": "pollution",
                        "errors": [],
                        "warnings": [],
                    }
                }
            },
        },
        400: {
            "description": "Erreur de validation",
            "content": {
                "application/json": {
                    "example": {
                        "state": "CRITICAL",
                        "valid": False,
                        "message": "Measurement rejected",
                        "errors": ["city is required"],
                        "warnings": [],
                    }
                }
            },
        },
    },
)
def validate(measurement: RawMeasurement, sensor_id: str | None = None):
    """Valide une mesure et la publie si NORMAL.
    `sensor_id` (optionnel, query param) : identifiant du capteur à l'origine
    de la mesure, transmis par `ingestion-service` qui le connaît déjà via
    sa propre route. Renvoyé tel quel dans la réponse, avec le flag
    `aberrant` qui permet à `ingestion-service` de savoir s'il doit
    considérer ce capteur en anomalie.
    """
    try:
        result = MeasurementValidator.validate(measurement, sensor_id=sensor_id)
        if result.state == "NORMAL" and result.measurement:
            _publish_measurement(result.measurement)
            return ValidationResponse(
                state=result.state,
                valid=True,
                aberrant=False,
                sensor_id=sensor_id,
                message="Measurement published to event bus",
                routing_key=result.measurement.type,
                errors=result.errors,
                warnings=result.warnings,
            )
        else:
            return ValidationResponse(
                state=result.state,
                valid=False,
                aberrant=result.aberrant,
                sensor_id=sensor_id,
                message="Measurement rejected (incomplete or anomalous data)",
                errors=result.errors,
                warnings=result.warnings,
            )
    except Exception as e:
        log.exception("Validation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/validate-batch",
    response_model=BatchValidationResponse,
    tags=["Validation"],
    summary="Valider un lot de mesures",
    description="""
    Valide un lot de mesures en une seule requête.
    Retourne le nombre total, acceptées (NORMAL) et rejetées (CRITICAL).
    """,
    responses={
        200: {
            "description": "Batch traité",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "state": "NORMAL",
                                "valid": True,
                                "message": "Measurement published to event bus",
                                "routing_key": "pollution",
                            }
                        ],
                        "total": 1,
                        "accepted": 1,
                        "rejected": 0,
                    }
                }
            },
        }
    },
)
def validate_batch(measurements: list[RawMeasurement]):
    """Valide un lot de mesures."""
    try:
        results = []
        accepted_count = 0
        rejected_count = 0
        for m in measurements:
            result = MeasurementValidator.validate(m)
            response = ValidationResponse(
                state=result.state,
                valid=result.valid,
                message=(
                    "Measurement published to event bus"
                    if result.state == "NORMAL"
                    else "Measurement rejected (incomplete or anomalous data)"
                ),
                routing_key=result.measurement.type if result.measurement else None,
                errors=result.errors,
                warnings=result.warnings,
            )
            if result.state == "NORMAL" and result.measurement:
                _publish_measurement(result.measurement)
                accepted_count += 1
                log.info(
                    "✓ [NORMAL] Published: %s from %s",
                    result.measurement.type,
                    result.measurement.city,
                )
            else:
                rejected_count += 1
                log.warning("✗ [CRITICAL] Not published: %s", result.errors)
            results.append(response)
        return BatchValidationResponse(
            results=results,
            total=len(measurements),
            accepted=accepted_count,
            rejected=rejected_count,
        )
    except Exception as e:
        log.exception("Batch validation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)