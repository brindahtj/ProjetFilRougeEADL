# python
import os
import sys
import time
import pika

RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")
RABBIT_PORT = int(os.getenv("RABBIT_PORT", "5672"))
RABBIT_USER = os.getenv("RABBIT_USER", "guest")
RABBIT_PASS = os.getenv("RABBIT_PASS", "guest")
RABBIT_VHOST = os.getenv("RABBIT_VHOST", "/")
RETRIES = int(os.getenv("RABBIT_RETRIES", "3"))
RETRY_DELAY = float(os.getenv("RABBIT_RETRY_DELAY", "2"))

def publish(message: str):
    creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    params = pika.ConnectionParameters(
        host=RABBIT_HOST,
        port=RABBIT_PORT,
        virtual_host=RABBIT_VHOST,
        credentials=creds,
        heartbeat=600,
        blocked_connection_timeout=300,
    )

    last_exc = None
    for attempt in range(1, RETRIES + 1):
        try:
            conn = pika.BlockingConnection(params)
            ch = conn.channel()
            ch.exchange_declare(exchange="logs", exchange_type="fanout", durable=True)
            ch.basic_publish(exchange="logs", routing_key="", body=message.encode("utf-8"))
            print(f" [x] Sent {message}")
            conn.close()
            return
        except Exception as e:
            last_exc = e
            print(f"Publish failed (attempt {attempt}/{RETRIES}): {e}")
            time.sleep(RETRY_DELAY)
    raise RuntimeError("Unable to publish after retries") from last_exc

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "Hello World!"
    publish(msg)