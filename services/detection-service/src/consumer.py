import json
import logging
import threading
import time
from typing import Dict, Any

import pika
import requests
from datetime import datetime

from .config import (
    RABBIT_HOST, RABBIT_USER, RABBIT_PASS, EXCHANGE,
    REFERENTIAL_URL, DEFAULTS, THRESHOLD_REFRESH_SECONDS, POLL_PREFETCH
)
from .models import PollutionMessage, TrafficMessage, AlertEvent

log = logging.getLogger("detection")
logging.basicConfig(level=logging.INFO)

class ThresholdCache:
    def __init__(self, referential_url: str = REFERENTIAL_URL):
        self.referential_url = referential_url
        self._lock = threading.Lock()
        self.values: Dict[str, float] = DEFAULTS.copy()
        self.last_load = None
        self.load()  # initial load
        # background refresher
        t = threading.Thread(target=self._periodic_refresh, daemon=True)
        t.start()

    def load(self):
        try:
            resp = requests.get(f"{self.referential_url}/thresholds")
            resp.raise_for_status()
            data = resp.json()  # list of thresholds
            with self._lock:
                self.values = DEFAULTS.copy()
                for t in data:
                    key = t.get("key")
                    val = t.get("value")
                    if key and val is not None:
                        self.values[key] = float(val)
                self.last_load = datetime.utcnow()
            log.info("Loaded %d thresholds from referential", len(self.values))
        except Exception as exc:
            log.warning("Failed to load thresholds from referential (%s). Using defaults. Error: %s", self.referential_url, exc)

    def _periodic_refresh(self):
        while True:
            time.sleep(THRESHOLD_REFRESH_SECONDS)
            try:
                self.load()
            except Exception:
                pass

    def get(self, key: str, default=None):
        with self._lock:
            return self.values.get(key, default)

# Global threshold cache
thresholds = ThresholdCache()

class DetectionConsumer:
    def __init__(self):
        creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
        params = pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds)
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()
        # use direct exchange to control routing keys
        self.ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)

        # queues for validated measurements
        self.ch.queue_declare(queue="q_pollution_validated", durable=True)
        self.ch.queue_declare(queue="q_traffic_validated", durable=True)

        self.ch.queue_bind(exchange=EXCHANGE, queue="q_pollution_validated", routing_key="pollution")
        self.ch.queue_bind(exchange=EXCHANGE, queue="q_traffic_validated", routing_key="traffic")

        self.ch.basic_qos(prefetch_count=POLL_PREFETCH)

    def start(self):
        log.info("Starting detection consumer...")
        self.ch.basic_consume(queue="q_pollution_validated", on_message_callback=self.on_pollution)
        self.ch.basic_consume(queue="q_traffic_validated", on_message_callback=self.on_traffic)
        try:
            self.ch.start_consuming()
        except KeyboardInterrupt:
            log.info("Interrupted, closing connection")
        finally:
            self.conn.close()

    def on_pollution(self, ch, method, properties, body):
        try:
            payload = json.loads(body)
            msg = PollutionMessage(**payload)
            self.detect_pollution(msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            log.exception("Error handling pollution message: %s", exc)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def on_traffic(self, ch, method, properties, body):
        try:
            payload = json.loads(body)
            msg = TrafficMessage(**payload)
            self.detect_traffic(msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            log.exception("Error handling traffic message: %s", exc)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def publish_alert(self, alert: AlertEvent):
        body = json.dumps(alert.dict(), default=str)
        self.ch.basic_publish(exchange=EXCHANGE, routing_key="alerts", body=body)
        log.info("Published alert: %s - %s", alert.type, alert.title)

    def detect_pollution(self, msg: PollutionMessage):
        if not msg.pollutant or msg.value is None:
            return

        # standardize key names e.g. NO2_WARNING
        key_base = (msg.pollutant or "").upper()
        warn_key = f"{key_base}_WARNING"
        crit_key = f"{key_base}_CRITICAL"

        crit = thresholds.get(crit_key, thresholds.get(f"{key_base}_CRITICAL", DEFAULTS.get("NO2_CRITICAL")))
        warn = thresholds.get(warn_key, thresholds.get(f"{key_base}_WARNING", DEFAULTS.get("NO2_WARNING")))

        # detection logic (simple fixed-threshold)
        if msg.value >= crit:
            alert = AlertEvent(
                type="pollution",
                level="CRITICAL",
                title=f"{msg.pollutant.upper()} above critical",
                message=f"{msg.pollutant.upper()} {msg.value} >= {crit}",
                city=msg.city,
                zone=msg.zone,
                pollutant=msg.pollutant,
                value=msg.value,
                unit=msg.unit,
                timestamp=msg.timestamp or datetime.utcnow(),
                metadata={"rule": "fixed_threshold", "threshold_key": crit_key}
            )
            self.publish_alert(alert)
        elif msg.value >= warn:
            alert = AlertEvent(
                type="pollution",
                level="WARNING",
                title=f"{msg.pollutant.upper()} above warning",
                message=f"{msg.pollutant.upper()} {msg.value} >= {warn}",
                city=msg.city,
                zone=msg.zone,
                pollutant=msg.pollutant,
                value=msg.value,
                unit=msg.unit,
                timestamp=msg.timestamp or datetime.utcnow(),
                metadata={"rule": "fixed_threshold", "threshold_key": warn_key}
            )
            self.publish_alert(alert)
        else:
            log.debug("Pollution within thresholds: %s %s", msg.pollutant, msg.value)

    def detect_traffic(self, msg: TrafficMessage):
        if msg.q is None:
            return

        warn_key = "TRAFFIC_Q_WARNING"
        crit_key = "TRAFFIC_Q_CRITICAL"

        crit = thresholds.get(crit_key, DEFAULTS.get("TRAFFIC_Q_CRITICAL"))
        warn = thresholds.get(warn_key, DEFAULTS.get("TRAFFIC_Q_WARNING"))

        if msg.q >= crit:
            alert = AlertEvent(
                type="traffic",
                level="CRITICAL",
                title=f"Traffic critical on {msg.section_id or msg.street}",
                message=f"q={msg.q} >= {crit}",
                city=msg.city,
                zone=msg.zone,
                street=msg.street,
                section_id=msg.section_id,
                value=msg.q,
                timestamp=msg.timestamp or datetime.utcnow(),
                metadata={"rule": "fixed_threshold", "threshold_key": crit_key}
            )
            self.publish_alert(alert)
        elif msg.q >= warn:
            alert = AlertEvent(
                type="traffic",
                level="WARNING",
                title=f"Traffic warning on {msg.section_id or msg.street}",
                message=f"q={msg.q} >= {warn}",
                city=msg.city,
                zone=msg.zone,
                street=msg.street,
                section_id=msg.section_id,
                value=msg.q,
                timestamp=msg.timestamp or datetime.utcnow(),
                metadata={"rule": "fixed_threshold", "threshold_key": warn_key}
            )
            self.publish_alert(alert)
        else:
            log.debug("Traffic normal: q=%s", msg.q)

if __name__ == "__main__":
    consumer = DetectionConsumer()
    consumer.start()