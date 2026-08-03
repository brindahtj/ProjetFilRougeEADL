
import json
from os import getenv
import random
import time
from datetime import datetime, timezone
import requests



RABBITMQ_USER = getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = getenv("RABBITMQ_PASS", "guest")
RABBITMQ_HOST = getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(getenv("RABBITMQ_PORT", "5672"))
EXCHANGE = getenv("RABBITMQ_EXCHANGE", "logs")
INGESTION_API_URL = getenv("INGESTION_API_URL", "http://ingestion:8005")
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

    # Attente de l'API HTTP
    for i in range(60):
        try:
            r = requests.get(f"{INGESTION_API_URL}/health", timeout=2)
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
                    f"{INGESTION_API_URL}/api/v1/sensors/{sensor_id}/metrics",
                    json=payload,
                    timeout=2,
                )
            except Exception as e:
                if n % 100 == 0:
                    print(f"[sim] warning : API POST failed : {e}")
    except KeyboardInterrupt:
        print("[sim] Arrêt du simulateur.")



if __name__ == "__main__":
    main()