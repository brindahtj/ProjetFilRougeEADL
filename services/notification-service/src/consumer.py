import pika, json, logging
from .config import RABBIT_HOST, RABBIT_USER, RABBIT_PASS, EXCHANGE

log = logging.getLogger("notification")
logging.basicConfig(level=logging.INFO)

class NotificationApp:
    def __init__(self):
        creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
        params = pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds)
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()
        self.ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)

        self.ch.queue_declare(queue="q_alerts", durable=True)
        self.ch.queue_bind(exchange=EXCHANGE, queue="q_alerts", routing_key="alerts")

    def start(self):
        self.ch.basic_consume(queue="q_alerts", on_message_callback=self.on_alert)
        log.info("Starting notification consumer")
        try:
            self.ch.start_consuming()
        finally:
            self.conn.close()

    def on_alert(self, ch, method, properties, body):
        try:
            msg = json.loads(body)
            # Here you would call webhook / email / push
            log.info("Received alert: %s", msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            log.exception("Alert handling error: %s", exc)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

if __name__ == "__main__":
    NotificationApp().start()