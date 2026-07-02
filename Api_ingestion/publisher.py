import json
import pika
from typing import Any

from Api_ingestion.config import (
    EXCHANGE,
    QUEUE,
    RABBIT_HOST,
    RABBIT_PORT,
    RABBIT_USER,
    RABBIT_PASS,
    RABBIT_VHOST,
)
from Api_ingestion.ports import AlertNotifier


class RabbitMQPublisher(AlertNotifier):
    def __init__(
        self,
        host=RABBIT_HOST,
        port=RABBIT_PORT,
        user=RABBIT_USER,
        password=RABBIT_PASS,
        vhost=RABBIT_VHOST,
    ):
        self._params = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=vhost,
            credentials=pika.PlainCredentials(user, password),
        )

    def _connect(self):
        return pika.BlockingConnection(self._params)

    def publish(self, message_data: Any, routing_key: str = "") -> None:
        payload = json.dumps(message_data) if isinstance(message_data, (dict, list)) else str(message_data)
        conn = self._connect()
        ch = conn.channel()
        ch.exchange_declare(exchange=EXCHANGE, exchange_type="fanout", durable=True)
        ch.queue_declare(queue=QUEUE, durable=True)
        ch.queue_bind(exchange=EXCHANGE, queue=QUEUE)
        ch.basic_publish(exchange=EXCHANGE, routing_key=routing_key, body=payload)
        conn.close()

    def notify(self, payload: Any, routing_key: str = "default") -> None:
        self.publish(payload, routing_key=routing_key)