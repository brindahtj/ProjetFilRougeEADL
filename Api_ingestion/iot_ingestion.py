# python
import os
import json
import csv
import time
import logging
import requests
import pandas as pd

from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from dotenv import load_dotenv; load_dotenv()

# =========================================================
# CONFIGURATION
# =========================================================

OPENAQ_BASE_URL = "https://api.openaq.org/v3"
HERE_TRAFFIC_URL = "https://data.traffic.hereapi.com/v7/flow"
HERE_API_KEY = os.getenv("HERE_API_KEY", "VOTRE_API_KEY_HERE")

OUTPUT_DIR = Path("data")
LOG_DIR = Path("logs")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "smart_city.log"),
        logging.StreamHandler()
    ]
)

log = logging.getLogger(__name__)

# =========================================================
# ZONES ÉTUDIÉES
# =========================================================

ZONES = [
    {"name": "Paris", "lat": 48.8566, "lon": 2.3522},
    {"name": "Lyon", "lat": 45.7640, "lon": 4.8357},
    {"name": "Marseille", "lat": 43.2965, "lon": 5.3698},
]

# =========================================================
# DATA CLASSES
# =========================================================

@dataclass
class PollutionReading:
    city: str
    pollutant: str
    value: float
    unit: str
    latitude: float
    longitude: float
    timestamp: str


@dataclass
class TrafficReading:
    city: str
    jam_factor: float
    current_speed: float
    free_flow_speed: float
    confidence: float
    latitude: float
    longitude: float
    timestamp: str

# =========================================================
# OPENAQ
# =========================================================

def fetch_openaq_data():
    url = f"{OPENAQ_BASE_URL}/locations"
    params = {"country": "FR", "limit": 100}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error(f"Erreur OpenAQ : {e}")
        return None


def extract_pollution_readings():
    data = fetch_openaq_data()
    if not data:
        return []

    pollution_readings = []
    results = data.get("results", [])

    for location in results:
        coordinates = location.get("coordinates") or {}
        latitude = coordinates.get("latitude")
        longitude = coordinates.get("longitude")

        # tolérance sur la structure des mesures
        sensors = (
            location.get("sensors")
            or location.get("parameters")
            or location.get("latestMeasurements")
            or location.get("measurements")
            or []
        )

        for sensor in sensors:
            # plusieurs formats possibles : dict ou simple str
            try:
                if isinstance(sensor, dict):
                    # différents noms de champs selon l'API
                    parameter = sensor.get("parameter") or sensor.get("name") or sensor.get("parameterName")
                    pollutant = parameter if isinstance(parameter, str) else (parameter.get("name") if isinstance(parameter, dict) else None)

                    # récupération de la dernière valeur
                    latest = sensor.get("lastValue") or sensor.get("latest") or sensor.get("value") or sensor.get("latestMeasurement")
                    if not latest:
                        # certains endpoints exposent un objet 'lastValue' ou 'latest' contenant value/datetime
                        latest_obj = sensor.get("latest") or sensor.get("lastValue")
                        if isinstance(latest_obj, dict):
                            value = latest_obj.get("value")
                            timestamp = latest_obj.get("datetime") or latest_obj.get("date")
                        else:
                            value = None
                            timestamp = None
                    else:
                        if isinstance(latest, dict):
                            value = latest.get("value")
                            timestamp = latest.get("datetime") or latest.get("date")
                        else:
                            value = latest
                            timestamp = None
                    unit = sensor.get("unit") or (sensor.get("units") if isinstance(sensor.get("units"), str) else None)
                else:
                    # format inattendu, sauter
                    continue

                if pollutant not in ["no2", "pm25", "pm10", "o3", "co"]:
                    continue
                if value is None:
                    continue

                reading = PollutionReading(
                    city=location.get("city", "Unknown"),
                    pollutant=pollutant,
                    value=float(value),
                    unit=unit or "",
                    latitude=latitude or 0.0,
                    longitude=longitude or 0.0,
                    timestamp=timestamp or datetime.utcnow().isoformat()
                )
                pollution_readings.append(reading)
            except Exception as e:
                log.debug(f"Ignored sensor entry due to parse error: {e}")
                continue

    return pollution_readings

# =========================================================
# HERE TRAFFIC API
# =========================================================

def fetch_traffic_data(lat, lon):
    params = {
        "in": f"circle:{lat},{lon};r=5000",
        "locationReferencing": "shape",
        "apiKey": HERE_API_KEY
    }

    try:
        response = requests.get(HERE_TRAFFIC_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log.error(f"Erreur HERE API : {e}")
        return None


def extract_traffic_readings():
    traffic_readings = []

    for zone in ZONES:
        data = fetch_traffic_data(zone["lat"], zone["lon"])
        if not data:
            continue

        results = data.get("results", []) or []
        for item in results:
            current_flow = item.get("currentFlow", {}) or {}
            try:
                reading = TrafficReading(
                    city=zone["name"],
                    jam_factor=float(current_flow.get("jamFactor", 0) or 0),
                    current_speed=float(current_flow.get("speed", 0) or 0),
                    free_flow_speed=float(current_flow.get("freeFlowSpeed", 0) or 0),
                    confidence=float(current_flow.get("confidence", 0) or 0),
                    latitude=zone["lat"],
                    longitude=zone["lon"],
                    timestamp=datetime.utcnow().isoformat()
                )
                traffic_readings.append(reading)
            except Exception:
                continue

    return traffic_readings

# =========================================================
# SAVE CSV
# =========================================================

def save_pollution_csv(readings):
    filepath = OUTPUT_DIR / "pollution.csv"
    exists = filepath.exists()
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "city", "pollutant", "value", "unit", "latitude", "longitude", "timestamp"
            ]
        )
        if not exists:
            writer.writeheader()
        for r in readings:
            writer.writerow(asdict(r))


def save_traffic_csv(readings):
    filepath = OUTPUT_DIR / "traffic.csv"
    exists = filepath.exists()
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "city", "jam_factor", "current_speed", "free_flow_speed", "confidence", "latitude", "longitude", "timestamp"
            ]
        )
        if not exists:
            writer.writeheader()
        for r in readings:
            # adapter clé jam_factor vs dataclass jam_factor
            row = asdict(r)
            # standardiser noms colonnes si nécessaire
            if "jam_factor" not in row and "jamFactor" in row:
                row["jam_factor"] = row.pop("jamFactor")
            writer.writerow(row)


# =========================================================
# PIPELINE
# =========================================================

import json
from publisher import send_message
def run_pipeline(n_cycles=5, interval_sec=60):
    log.info("🚀 SMART CITY PIPELINE")
    for cycle in range(1, n_cycles + 1):
        log.info("Cycle %d/%d", cycle, n_cycles)
        pollution = extract_pollution_readings()
        traffic = extract_traffic_readings()

        if pollution:
            save_pollution_csv(pollution)
            send_message([asdict(r) for r in pollution], routing_key="pollution")
            log.info("✅ %d mesures pollution publiées", len(pollution))

        if traffic:
            save_traffic_csv(traffic)
            send_message([asdict(r) for r in traffic], routing_key="traffic")
            log.info("✅ %d mesures trafic publiées", len(traffic))

        if cycle < n_cycles:
            time.sleep(interval_sec)
    log.info("🏁 Pipeline terminé")

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    run_pipeline(n_cycles=5, interval_sec=60)