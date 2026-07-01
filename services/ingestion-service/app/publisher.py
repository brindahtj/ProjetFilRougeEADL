import json
import logging
import pika
from .config import RABBIT_HOST, RABBIT_PORT, RABBIT_USER, RABBIT_PASS, EXCHANGE

log = logging.getLogger(__name__)

class RabbitPublisher:
    def __init__(self, host=RABBIT_HOST, port=RABBIT_PORT, user=RABBIT_USER, password=RABBIT_PASS, exchange=EXCHANGE):
        self.exchange = exchange
        credentials = pika.PlainCredentials(user, password)
        params = pika.ConnectionParameters(host=host, port=port, credentials=credentials)
        self.params = params

    def publish(self, routing_key: str, payload):
        body = json.dumps(payload, default=str)
        try:
            conn = pika.BlockingConnection(self.params)
            ch = conn.channel()
            ch.exchange_declare(exchange=self.exchange, exchange_type="direct", durable=True)
            ch.basic_publish(exchange=self.exchange, routing_key=routing_key, body=body)
            conn.close()
            log.debug("Published to %s: %s", routing_key, body)
        except Exception as exc:
            log.exception("Failed to publish: %s", exc)
            raise