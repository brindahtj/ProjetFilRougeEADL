import pika
import json
import sys

RABBIT_HOST = "localhost"
RABBIT_PORT = 5672
RABBIT_USER = "guest"
RABBIT_PASS = "guest"
RABBIT_VHOST = "/"
EXCHANGE = "logs"

def send_message(trafic, no2):
    """Envoie un message JSON au publisher."""
    creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    params = pika.ConnectionParameters(
        host=RABBIT_HOST,
        port=RABBIT_PORT,
        virtual_host=RABBIT_VHOST,
        credentials=creds,
    )

    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="fanout", durable=True)

    # Créer le message JSON
    message = json.dumps({
        "trafic": trafic,
        "no2": no2
    })

    ch.basic_publish(exchange=EXCHANGE, routing_key="", body=message)
    print(f"Message envoyé: {message}")

    conn.close()

if __name__ == "__main__":
    # Utilisation: python publisher.py 45.5 120.3
    if len(sys.argv) == 3:
        trafic = float(sys.argv[1])
        no2 = float(sys.argv[2])
        send_message(trafic, no2)
    else:
        print("Usage: python publisher.py <trafic> <no2>")