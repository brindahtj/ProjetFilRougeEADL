import os
import csv
import time
import logging
import requests
import pandas as pd

from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

from alert_policy import AlertPolicy
from monitoring.metrics import METRICS
from Api_ingestion.messaging.publisher import publish_alert

load_dotenv()

# =========================================================
# CONFIGURATION
# =========================================================

OPENAQ_BASE_URL = "https://api.openaq.org/v3"
HERE_TRAFFIC_URL = "https://data.traffic.hereapi.com/v7/flow"

HERE_API_KEY = os.getenv(
    "HERE_API_KEY",
    "VOTRE_API_KEY_HERE"
)

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
# ZONES
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

    params = {
        "country": "FR",
        "limit": 100
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as exc:

        log.error("Erreur OpenAQ : %s", exc)

        return None

# =========================================================
# EXTRACTION POLLUTION
# =========================================================

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

        sensors = (
            location.get("sensors")
            or location.get("parameters")
            or location.get("latestMeasurements")
            or []
        )

        for sensor in sensors:

            try:

                parameter = (
                    sensor.get("parameter")
                    or sensor.get("name")
                )

                pollutant = (
                    parameter
                    if isinstance(parameter, str)
                    else None
                )

                value = (
                    sensor.get("value")
                    or sensor.get("lastValue")
                )

                if pollutant not in [
                    "no2",
                    "pm25",
                    "pm10",
                    "o3",
                    "co"
                ]:
                    continue

                if value is None:
                    continue

                reading = PollutionReading(
                    city=location.get("city", "Unknown"),
                    pollutant=pollutant,
                    value=float(value),
                    unit=sensor.get("unit", ""),
                    latitude=latitude or 0.0,
                    longitude=longitude or 0.0,
                    timestamp=datetime.utcnow().isoformat()
                )

                pollution_readings.append(reading)

            except Exception as exc:

                log.warning(
                    "Parsing sensor error : %s",
                    exc
                )

                continue

    return pollution_readings

# =========================================================
# TRAFFIC
# =========================================================

def fetch_traffic_data(lat, lon):

    params = {
        "in": f"circle:{lat},{lon};r=5000",
        "locationReferencing": "shape",
        "apiKey": HERE_API_KEY
    }

    try:

        response = requests.get(
            HERE_TRAFFIC_URL,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as exc:

        log.error("Erreur HERE API : %s", exc)

        return None

# =========================================================
# EXTRACTION TRAFFIC
# =========================================================

def extract_traffic_readings():

    traffic_readings = []

    for zone in ZONES:

        data = fetch_traffic_data(
            zone["lat"],
            zone["lon"]
        )

        if not data:
            continue

        results = data.get("results", [])

        for item in results:

            current_flow = item.get(
                "currentFlow",
                {}
            )

            reading = TrafficReading(
                city=zone["name"],
                jam_factor=float(
                    current_flow.get("jamFactor", 0)
                ),
                current_speed=float(
                    current_flow.get("speed", 0)
                ),
                free_flow_speed=float(
                    current_flow.get(
                        "freeFlowSpeed",
                        0
                    )
                ),
                confidence=float(
                    current_flow.get(
                        "confidence",
                        0
                    )
                ),
                latitude=zone["lat"],
                longitude=zone["lon"],
                timestamp=datetime.utcnow().isoformat()
            )

            traffic_readings.append(reading)

    return traffic_readings

# =========================================================
# SAVE CSV
# =========================================================

def save_pollution_csv(readings):

    filepath = OUTPUT_DIR / "pollution.csv"

    exists = filepath.exists()

    with open(
        filepath,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "city",
                "pollutant",
                "value",
                "unit",
                "latitude",
                "longitude",
                "timestamp"
            ]
        )

        if not exists:
            writer.writeheader()

        for reading in readings:
            writer.writerow(asdict(reading))


def save_traffic_csv(readings):

    filepath = OUTPUT_DIR / "traffic.csv"

    exists = filepath.exists()

    with open(
        filepath,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "city",
                "jam_factor",
                "current_speed",
                "free_flow_speed",
                "confidence",
                "latitude",
                "longitude",
                "timestamp"
            ]
        )

        if not exists:
            writer.writeheader()

        for reading in readings:
            writer.writerow(asdict(reading))

# =========================================================
# ALERTS
# =========================================================

def publish_pollution_alerts(pollution_readings):

    policy = AlertPolicy(
        threshold=80,
        consecutive_count=2
    )

    grouped_values = {}

    for reading in pollution_readings:

        if reading.pollutant != "no2":
            continue

        key = (
            reading.city,
            reading.pollutant
        )

        if key not in grouped_values:
            grouped_values[key] = []

        grouped_values[key].append(reading.value)

        alert_event = policy.create_alert_if_needed(
            city=reading.city,
            pollutant=reading.pollutant,
            values=grouped_values[key]
        )

        if alert_event:

            publish_alert(
                alert_event.to_dict()
            )

# =========================================================
# CORRELATION
# =========================================================

def compute_correlation(
    pollution_readings,
    traffic_readings
):

    if not pollution_readings:
        return None

    if not traffic_readings:
        return None

    pollution_df = pd.DataFrame(
        [asdict(r) for r in pollution_readings]
    )

    traffic_df = pd.DataFrame(
        [asdict(r) for r in traffic_readings]
    )

    no2_df = pollution_df[
        pollution_df["pollutant"] == "no2"
    ]

    pollution_grouped = no2_df.groupby(
        "city"
    )["value"].mean()

    traffic_grouped = traffic_df.groupby(
        "city"
    )["jam_factor"].mean()

    merged = pd.concat(
        [pollution_grouped, traffic_grouped],
        axis=1,
        join="inner"
    ).dropna()

    merged.columns = [
        "avg_no2",
        "avg_jam"
    ]

    correlation = merged[
        "avg_no2"
    ].corr(
        merged["avg_jam"]
    )

    log.info(
        "Corrélation NO2/Trafic = %.4f",
        correlation
    )

    return correlation

# =========================================================
# PIPELINE
# =========================================================

def run_pipeline(
    n_cycles=5,
    interval_sec=60
):

    log.info("SMART CITY PIPELINE START")

    for cycle in range(
        1,
        n_cycles + 1
    ):

        log.info(
            "Cycle %s/%s",
            cycle,
            n_cycles
        )

        pollution = extract_pollution_readings()

        traffic = extract_traffic_readings()

        if pollution:
            save_pollution_csv(pollution)
            publish_pollution_alerts(pollution)

        if traffic:
            save_traffic_csv(traffic)

        compute_correlation(
            pollution,
            traffic
        )

        log.info(
            "pollution_count=%s traffic_count=%s",
            len(pollution),
            len(traffic)
        )

        if cycle < n_cycles:
            time.sleep(interval_sec)

    log.info("PIPELINE FINISHED")

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    run_pipeline(
        n_cycles=5,
        interval_sec=60
    )