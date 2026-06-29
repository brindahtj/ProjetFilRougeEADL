import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OPENAQ_BASE_URL = "https://api.openaq.org/v3"
HERE_TRAFFIC_URL = "https://data.traffic.hereapi.com/v7/flow"
TRAFFIC_API_KEY = os.getenv("TRAFFIC_API_KEY")

OUTPUT_DIR = Path("data")
LOG_DIR = Path("logs")

RABBIT_HOST = os.getenv("RABBIT_HOST")
RABBIT_PORT = int(os.getenv("RABBIT_PORT"))
RABBIT_USER = os.getenv("RABBIT_USER")
RABBIT_PASS = os.getenv("RABBIT_PASS")
RABBIT_VHOST = os.getenv("RABBIT_VHOST")
EXCHANGE = os.getenv("RABBIT_EXCHANGE")
RABBIT_QUEUE = os.getenv("RABBIT_QUEUE")

ZONES = [
    {"name": "Paris", "lat": 48.8566, "lon": 2.3522},
    {"name": "Lyon", "lat": 45.7640, "lon": 4.8357},
    {"name": "Marseille", "lat": 43.2965, "lon": 5.3698},
]

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_POLLUTION_FIELDS = [
    "city",
    "pollutant",
    "value",
    "unit",
    "latitude",
    "longitude",
    "timestamp",
]

DEFAULT_TRAFFIC_FIELDS = [
    "city",
    "jam_factor",
    "current_speed",
    "free_flow_speed",
    "confidence",
    "latitude",
    "longitude",
    "timestamp",
]


def setup_logging(log_dir: Path):
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "smart_city.log"),
            logging.StreamHandler(),
        ],
    )
