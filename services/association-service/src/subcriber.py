import pika
import json
import logging
from .config import RABBIT_HOST, RABBIT_USER, RABBIT_PASS, EXCHANGE, BUFFER_SIZE, TIME_WINDOW_MINUTES
from .association import AssociationEngine

log = logging.getLogger("association")
logging.basicConfig(level=logging.INFO)

class AssociationSubscriber:
    def __init__(self):
        creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
        params = pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds)
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()
        self.ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)

        # Create queues
        self.ch.queue_declare(queue="q_pollution_assoc", durable=True)
        self.ch.queue_declare(queue="q_traffic_assoc", durable=True)
        self.ch.queue_bind(exchange=EXCHANGE, queue="q_pollution_assoc", routing_key="pollution")
        self.ch.queue_bind(exchange=EXCHANGE, queue="q_traffic_assoc", routing_key="traffic")

        self.pollution_buffer = []
        self.traffic_buffer = []
        self.engine = AssociationEngine(time_window_minutes=TIME_WINDOW_MINUTES)

    def start(self):
        self.ch.basic_qos(prefetch_count=1)
        self.ch.basic_consume(queue="q_pollution_assoc", on_message_callback=self.on_pollution)
        self.ch.basic_consume(queue="q_traffic_assoc", on_message_callback=self.on_traffic)
        log.info("🚀 Association service starting")
        try:
            self.ch.start_consuming()
        finally:
            self.conn.close()

    def on_pollution(self, ch, method, properties, body):
        try:
            msg = json.loads(body)
            self.pollution_buffer.append(msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            self.try_associate()
        except Exception as exc:
            log.exception("Pollution handling error: %s", exc)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def on_traffic(self, ch, method, properties, body):
        try:
            msg = json.loads(body)
            self.traffic_buffer.append(msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            self.try_associate()
        except Exception as exc:
            log.exception("Traffic handling error: %s", exc)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def try_associate(self):
        """Associe si buffers ont assez de données."""
        if len(self.pollution_buffer) >= BUFFER_SIZE and len(self.traffic_buffer) >= BUFFER_SIZE:
            associations = self.engine.associate_by_zone_and_time(
                self.pollution_buffer,
                self.traffic_buffer
            )

            for assoc in associations:
                # Publier association event
                body = json.dumps(assoc.dict(), default=str)
                self.ch.basic_publish(
                    exchange=EXCHANGE,
                    routing_key="association",
                    body=body
                )
                log.info("Published association event: %s", assoc.dict())

            # Clear buffers (ou stratégie plus sophistiquée)
            self.pollution_buffer = []
            self.traffic_buffer = []

if __name__ == "__main__":
    AssociationSubscriber().start()