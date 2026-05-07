import pika
import json

RABBIT_HOST = "localhost"
RABBIT_PORT = 5672
RABBIT_USER = "guest"
RABBIT_PASS = "guest"
RABBIT_VHOST = "/"
EXCHANGE = "logs"
QUEUE = "moteur_correlation"

def send_message(message_data, routing_key="pollution"):
    """Envoie un message JSON au broker RabbitMQ.

    Args:
        message_data: dict, list ou str à sérialiser en JSON
        routing_key: clé de routage (défaut: 'pollution')
    """
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
    ch.queue_declare(queue=QUEUE, durable=True)
    ch.queue_bind(exchange=EXCHANGE, queue=QUEUE)

    # Sérialiser en JSON si nécessaire
    if isinstance(message_data, (dict, list)):
        message = json.dumps(message_data)
    else:
        message = str(message_data)

    ch.basic_publish(exchange=EXCHANGE, routing_key=routing_key, body=message)
    print(f"✅ Message envoyé: {message[:100]}...")

    conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        send_message(sys.argv[1])
    else:
        print("Usage: python publisher.py '<json_message>'")