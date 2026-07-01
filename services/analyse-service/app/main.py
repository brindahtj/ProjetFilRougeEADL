import logging
import pika
import json
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .config import RABBIT_HOST, RABBIT_USER, RABBIT_PASS, EXCHANGE
from .database import save_correlation, get_correlations, SessionLocal, CorrelationORM
from .models import CorrelationResponse
from typing import List

log = logging.getLogger("analyse")
logging.basicConfig(level=logging.INFO)

consumer_thread = None

def init_consumer():
    """Lance le consumer RabbitMQ dans un thread séparé."""
    import threading

    def consume():
        creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
        params = pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds)
        conn = pika.BlockingConnection(params)
        ch = conn.channel()
        ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)

        ch.queue_declare(queue="q_association", durable=True)
        ch.queue_bind(exchange=EXCHANGE, queue="q_association", routing_key="association")

        def on_association(ch, method, properties, body):
            try:
                msg = json.loads(body)
                save_correlation(
                    city=msg["city"],
                    zone=msg.get("zone"),
                    pollution_avg=msg["pollution_avg"],
                    traffic_avg=msg["traffic_avg"],
                    time_window=msg.get("time_window", "")
                )
                log.info("Stored correlation: %s/%s", msg["city"], msg.get("zone"))
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as exc:
                log.exception("Error storing correlation: %s", exc)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        ch.basic_consume(queue="q_association", on_message_callback=on_association)
        log.info("🔄 Analyse service consumer started")
        ch.start_consuming()

    thread = threading.Thread(target=consume, daemon=True)
    thread.start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_consumer()
    yield
    # Shutdown

app = FastAPI(title="Analyse Service", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/correlations", response_model=List[CorrelationResponse])
def get_all_correlations(city: str = None, zone: str = None, limit: int = 100):
    """Récupère les corrélations pollution-trafic calculées."""
    correlations = get_correlations(city=city, zone=zone, limit=limit)
    return correlations

@app.get("/correlations/{city}", response_model=List[CorrelationResponse])
def get_city_correlations(city: str, zone: str = None, limit: int = 50):
    """Récupère les corrélations pour une ville."""
    correlations = get_correlations(city=city, zone=zone, limit=limit)
    return correlations

@app.get("/correlations/{city}/{zone}", response_model=List[CorrelationResponse])
def get_zone_correlations(city: str, zone: str, limit: int = 50):
    """Récupère les corrélations pour une zone."""
    correlations = get_correlations(city=city, zone=zone, limit=limit)
    return correlations