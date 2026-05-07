import os
import json
import time
import logging
import pika

from dotenv import load_dotenv
from Api_ingestion.monitoring.metrics import METRICS

load_dotenv()

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

log = logging.getLogger(__name__)

# =========================================================
# CONFIGURATION
# =========================================================

RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")
RABBIT_PORT = int(os.getenv("RABBIT_PORT", "5672"))
RABBIT_USER = os.getenv("RABBIT_USER", "guest")
RABBIT_PASS = os.getenv("RABBIT_PASS", "guest")
RABBIT_VHOST = os.getenv("RABBIT_VHOST", "/")

RETRIES = int(os.getenv("RABBIT_RETRIES", "3"))
RETRY_DELAY = float(os.getenv("RABBIT_RETRY_DELAY", "2"))

EXCHANGE = "air.alerts"
DLQ_EXCHANGE = "air.alerts.dlx"

# =========================================================
# CONNECTION
# =========================================================

def get_connection():

    credentials = pika.PlainCredentials(
        RABBIT_USER,
        RABBIT_PASS
    )

    params = pika.ConnectionParameters(
        host=RABBIT_HOST,
        port=RABBIT_PORT,
        virtual_host=RABBIT_VHOST,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300,
    )

    return pika.BlockingConnection(params)

# =========================================================
# PUBLISH ALERT
# =========================================================

def publish_alert(event: dict):

    message = json.dumps(event)

    last_exception = None

    for attempt in range(1, RETRIES + 1):

        try:

            connection = get_connection()
            channel = connection.channel()

            # Exchange principal
            channel.exchange_declare(
                exchange=EXCHANGE,
                exchange_type="fanout",
                durable=True,
            )

            # DLQ Exchange
            channel.exchange_declare(
                exchange=DLQ_EXCHANGE,
                exchange_type="fanout",
                durable=True,
            )

            channel.basic_publish(
                exchange=EXCHANGE,
                routing_key="",
                body=message.encode("utf-8"),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                    headers={
                        "event_id": event.get("event_id"),
                        "event_type": "AirQualityAlertEvent",
                        "schema_version": "v1",
                    },
                ),
            )

            METRICS["alerts_published_total"] += 1

            log.info(
                "event_id=%s city=%s pollutant=%s severity=%s published=true",
                event.get("event_id"),
                event.get("city"),
                event.get("pollutant"),
                event.get("severity"),
            )

            connection.close()

            return True

        except Exception as exc:

            METRICS["retry_total"] += 1
            METRICS["publish_failures_total"] += 1

            last_exception = exc

            log.error(
                "publish_failed attempt=%s/%s error=%s",
                attempt,
                RETRIES,
                exc
            )

            time.sleep(RETRY_DELAY)

    raise RuntimeError(
        "Unable to publish alert after retries"
    ) from last_exception