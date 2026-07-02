import logging
import pika
import json
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .models import RawMeasurement
from .validator import MeasurementValidator
from .config import RABBIT_HOST, RABBIT_USER, RABBIT_PASS, EXCHANGE

log = logging.getLogger("validation")
logging.basicConfig(level=logging.INFO)

# RabbitMQ connection
publisher_connection = None

def init_rabbit():
    """Initialise la connexion RabbitMQ."""
    global publisher_connection
    creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    params = pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds)
    publisher_connection = pika.BlockingConnection(params)
    ch = publisher_connection.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
    log.info("RabbitMQ initialized")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_rabbit()
    yield
    if publisher_connection:
        publisher_connection.close()

app = FastAPI(title="Validation Service", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/validate")
def validate(measurement: RawMeasurement):
    """Valide une mesure et la publie si NORMAL."""
    result = MeasurementValidator.validate(measurement)

    if result.state == "NORMAL" and result.measurement:
        # Donnée complète et normale → publier
        ch = publisher_connection.channel()
        routing_key = result.measurement.type  # "pollution" ou "traffic"
        body = json.dumps(result.measurement.dict(), default=str)
        ch.basic_publish(exchange=EXCHANGE, routing_key=routing_key, body=body)
        log.info("✓ [NORMAL] Published to %s: %s", routing_key, result.measurement.city)
        return {
            "state": result.state,
            "valid": True,
            "message": "Measurement published to event bus",
            "routing_key": routing_key
        }
    else:
        log.warning("✗ [CRITICAL] Measurement rejected: %s", result.errors)
        return {
            "state": result.state,
            "valid": False,
            "message": "Measurement rejected (incomplete or anomalous data)",
            "errors": result.errors,
            "warnings": result.warnings
        }

@app.post("/validate-batch")
def validate_batch(measurements: list[RawMeasurement]):
    """Valide un lot de mesures."""
    results = []
    for m in measurements:
        result = MeasurementValidator.validate(m)

        response = {
            "state": result.state,
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings
        }


        if result.state == "NORMAL" and result.measurement:
            ch = publisher_connection.channel()
            routing_key = result.measurement.type
            body = json.dumps(result.measurement.dict(), default=str)
            ch.basic_publish(exchange=EXCHANGE, routing_key=routing_key, body=body)
            response["published"] = True
            log.info("✓ [NORMAL] Published: %s from %s", result.measurement.type, result.measurement.city)
        else:
            response["published"] = False
            log.warning("✗ [CRITICAL] Not published: %s", result.errors)

        results.append(response)

    return {"results": results}