import json
import logging

import pika

from Api_ingestion.config import (
    EXCHANGE,
    RABBIT_QUEUE,
    RABBIT_HOST,
    RABBIT_PASS,
    RABBIT_PORT,
    RABBIT_USER,
    RABBIT_VHOST,
)
from Api_ingestion.exceptions import PublisherError

log = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(
        self,
        host=RABBIT_HOST,
        port=RABBIT_PORT,
        user=RABBIT_USER,
        password=RABBIT_PASS,
        vhost=RABBIT_VHOST,
    ):
        self._connection_parameters = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=vhost,
            credentials=pika.PlainCredentials(user, password),
        )

    def publish(self, message_data, routing_key="pollution"):
        payload = (
            json.dumps(message_data)
            if isinstance(message_data, (dict, list))
            else str(message_data)
        )

        try:
            connection = pika.BlockingConnection(self._connection_parameters)
            channel = connection.channel()
            channel.exchange_declare(
                exchange=EXCHANGE, exchange_type="fanout", durable=True
            )
            channel.queue_declare(queue=RABBIT_QUEUE, durable=True)
            channel.queue_bind(exchange=EXCHANGE, queue=RABBIT_QUEUE)
            channel.basic_publish(
                exchange=EXCHANGE, routing_key=routing_key, body=payload
            )
            connection.close()
            log.debug(f"Message publié sur {routing_key}")
        except pika.exceptions.AMQPError as exc:
            raise PublisherError(f"Erreur RabbitMQ : {exc}") from exc


def send_message(message_data, routing_key="pollution"):
    RabbitMQPublisher().publish(message_data, routing_key=routing_key)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        send_message(sys.argv[1])
    else:
        print("Usage: python publisher.py '<json_message>'")