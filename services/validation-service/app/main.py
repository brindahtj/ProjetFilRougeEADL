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
    # Startup
    init_rabbit()
    yield
    # Shutdown
    if publisher_connection:
        publisher_connection.close()

app = FastAPI(title="Validation Service", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/validate")
def validate(measurement: RawMeasurement):
    """Valide une mesure et la publie si OK."""
    result = MeasurementValidator.validate(measurement)

    if result.valid and result.measurement:
        # Publier sur RabbitMQ
        ch = publisher_connection.channel()
        routing_key = result.measurement.type  # "pollution" ou "traffic"
        body = json.dumps(result.measurement.dict(), default=str)
        ch.basic_publish(exchange=EXCHANGE, routing_key=routing_key, body=body)
        log.info("Published to %s", routing_key)
        return {
            "valid": True,
            "message": "Measurement published to event bus",
            "routing_key": routing_key
        }
    else:
        return {
            "valid": False,
            "errors": result.errors,
            "warnings": result.warnings
        }

@app.post("/validate-batch")
def validate_batch(measurements: list[RawMeasurement]):
    """Valide un lot de mesures."""
    results = []
    for m in measurements:
        result = MeasurementValidator.validate(m)
        if result.valid and result.measurement:
            ch = publisher_connection.channel()
            routing_key = result.measurement.type
            body = json.dumps(result.measurement.dict(), default=str)
            ch.basic_publish(exchange=EXCHANGE, routing_key=routing_key, body=body)

        results.append({
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings
        })

    return {"results": results}