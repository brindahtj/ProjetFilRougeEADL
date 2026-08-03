
import json
from os import getenv
import random
import time
from datetime import datetime, timezone

import pika
import requests



RABBITMQ_USER = getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = getenv("RABBITMQ_PASS", "guest")
RABBITMQ_HOST = getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_QUEUE= getenv("RABBITMQ_QUEUE")
EXCHANGE = getenv("RABBITMQ_EXCHANGE", "logs")
TARGET_API_URL = getenv("TARGET_API_URL", "http://api-python:8000")
RATE           = int(getenv("MEASUREMENTS_PER_SECOND", "10"))

# Catalogue de capteurs (Air et Trafic uniquement)
SENSORS = [
    ("TRAF-001", "traffic"), ("TRAF-002", "traffic"), ("TRAF-003", "traffic"),
    ("AIR-001",  "air"),     ("AIR-002",  "air"),     ("AIR-003",  "air"),
]

METRICS = {
    "traffic": [
        ("vehicles_per_min", "veh/min", (5, 120)),
        ("avg_speed_kmh",    "km/h",    (10, 90)),
    ],
    "air": [
        ("co2",  "ppm",   (350, 900)),
        ("pm25", "µg/m³", (5, 120)),   # >75 => alerte critical
        ("no2",  "µg/m³", (5, 200)),
    ],
}


def build_rabbitmq_channel(retries=30):
    """Connexion à RabbitMQ avec retry pattern."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )

    for i in range(retries):
        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            # Déclaration de la queue pour s'assurer qu'elle existe
            channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            print(f"[sim] Connecté à RabbitMQ sur {RABBITMQ_HOST}:{RABBITMQ_PORT}")
            return connection, channel
        except pika.exceptions.AMQPConnectionError:
            print(f"[sim] RabbitMQ pas prêt (essai {i+1}/{retries}), retry dans 3s…")
            time.sleep(3)

    raise RuntimeError("RabbitMQ indisponible après retries")


def generate_measurement():
    ext_id, stype = random.choice(SENSORS)
    metric, unit, (lo, hi) = random.choice(METRICS[stype])
    value = round(random.uniform(lo, hi), 2)

    # Injection périodique d'une valeur hors bornes pour déclencher les alertes (PM2.5)
    if random.random() < 0.03:
        if metric == "pm25":
            value = round(random.uniform(80, 200), 2)

    return {
        "sensor_external_id": ext_id,
        "sensor_type": stype,
        "metric": metric,
        "value": value,
        "unit": unit,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    print(f"[sim] Démarrage — RabbitMQ={RABBITMQ_HOST}:{RABBITMQ_PORT} queue={RABBITMQ_QUEUE} api={TARGET_API_URL} rate={RATE}/s")

    connection, channel = build_rabbitmq_channel()

    # Attente de l'API HTTP
    for i in range(60):
        try:
            r = requests.get(f"{TARGET_API_URL}/health", timeout=2)
            if r.status_code == 200:
                print(f"[sim] API prête : {r.json()}")
                break
        except Exception:
            pass
        print(f"[sim] API pas prête (essai {i+1}/60), retry dans 3s…")
        time.sleep(3)

    interval = 1.0 / RATE
    n = 0

    try:
        while True:
            m = generate_measurement()

            # Publication dans RabbitMQ
            try:
                channel.basic_publish(
                    exchange='',
                    routing_key=RABBITMQ_QUEUE,
                    body=json.dumps(m),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # Rendre le message persistant
                        content_type='application/json'
                    )
                )
            except pika.exceptions.AMQPError as e:
                print(f"[sim] Erreur d'envoi RabbitMQ : {e}")
                # Essai de reconnexion en cas de coupure
                connection, channel = build_rabbitmq_channel()

            # Post HTTP direct vers l'API
                # Post HTTP direct vers l'API
            try:
                # 1. On extrait l'ID du capteur pour l'URL
                sensor_id = m["sensor_external_id"]

                # 2. On prépare la liste de métriques dans le format attendu par SensorMetricIn
                payload = [
                    {
                        "metric": m["metric"],
                        "value": m["value"],
                        "unit": m["unit"],
                        "recorded_at": m["recorded_at"],
                    }
                ]

                # 3. On appelle la bonne route FastApi
                requests.post(
                    f"{TARGET_API_URL}/api/v1/sensors/{sensor_id}/metrics",
                    json=payload,
                    timeout=2,
                )
            except Exception as e:
                if n % 100 == 0:
                    print(f"[sim] warning : API POST failed : {e}")

    except KeyboardInterrupt:
        print("[sim] Arrêt du simulateur.")
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    main()