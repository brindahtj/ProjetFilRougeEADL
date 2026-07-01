import pika, json, logging, time
from .config import RABBIT_HOST, RABBIT_USER, RABBIT_PASS, EXCHANGE, BUFFER_SIZE
from .correlation import pearson

log = logging.getLogger("correlation")
logging.basicConfig(level=logging.INFO)

class CorrelationApp:
    def __init__(self):
        creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
        params = pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds)
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()
        self.ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)

        # Create dedicated queues and bind
        self.ch.queue_declare(queue="q_pollution", durable=True)
        self.ch.queue_declare(queue="q_traffic", durable=True)
        self.ch.queue_bind(exchange=EXCHANGE, queue="q_pollution", routing_key="pollution")
        self.ch.queue_bind(exchange=EXCHANGE, queue="q_traffic", routing_key="traffic")

        self.pollution_buffer = []
        self.traffic_buffer = []

    def start(self):
        self.ch.basic_qos(prefetch_count=10)
        self.ch.basic_consume(queue="q_pollution", on_message_callback=self.on_pollution)
        self.ch.basic_consume(queue="q_traffic", on_message_callback=self.on_traffic)
        log.info("Starting correlation consumer")
        try:
            self.ch.start_consuming()
        finally:
            self.conn.close()

    def on_pollution(self, ch, method, properties, body):
        try:
            msg = json.loads(body)
            # expect msg to contain city and value
            self.pollution_buffer.append(msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            self.try_compute()
        except Exception as exc:
            log.exception("pollution handle error: %s", exc)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def on_traffic(self, ch, method, properties, body):
        try:
            msg = json.loads(body)
            self.traffic_buffer.append(msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            self.try_compute()
        except Exception as exc:
            log.exception("traffic handle error: %s", exc)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def try_compute(self):
        # Very simple: group by city, if both buffers have entries for a city, compute correlation
        cities = set([p.get("city") for p in self.pollution_buffer if p.get("city")] + [t.get("city") for t in self.traffic_buffer if t.get("city")])
        for city in cities:
            poll_vals = [float(p["value"]) for p in self.pollution_buffer if p.get("city")==city and p.get("value") is not None]
            traf_vals = [float(t["q"]) for t in self.traffic_buffer if t.get("city")==city and t.get("q") is not None]
            # align to min length by time order (naive)
            n = min(len(poll_vals), len(traf_vals))
            if n >= 2:
                corr = pearson(poll_vals[-n:], traf_vals[-n:])
                if corr is not None:
                    event = {"city": city, "corr_value": corr, "sample_size": n}
                    # publish to exchange with routing 'correlation'
                    self.publish("correlation", event)
                    log.info("Correlation for %s = %s (n=%d)", city, corr, n)
                    # remove used items to avoid recompute (simple strategy)
                    # drop oldest n
                    self.pollution_buffer = [p for p in self.pollution_buffer if p.get("city")!=city or p in self.pollution_buffer[-(len(self.pollution_buffer)-n):]]
                    self.traffic_buffer = [t for t in self.traffic_buffer if t.get("city")!=city or t in self.traffic_buffer[-(len(self.traffic_buffer)-n):]]

    def publish(self, routing_key, payload):
        body = json.dumps(payload, default=str)
        self.ch.basic_publish(exchange=EXCHANGE, routing_key=routing_key, body=body)

if __name__ == "__main__":
    app = CorrelationApp()
    app.start()