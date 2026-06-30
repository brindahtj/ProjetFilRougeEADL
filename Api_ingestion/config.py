import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OPENAQ_BASE_URL = "https://api.openaq.org/v3"
OPENAQ_COUNTRY = "FR"

# API Paris OpenData - pas de clé requise
PARIS_TRAFFIC_BASE_URL = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/comptages-routiers-permanents/records"
PARIS_TRAFFIC_LIMIT = 100

AIR_API_KEY = os.getenv("AIR_API_KEY")

OUTPUT_DIR = Path("data")
LOG_DIR = Path("logs")

RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")
RABBIT_PORT = int(os.getenv("RABBIT_PORT", 5672))
RABBIT_USER = os.getenv("RABBIT_USER", "guest")
RABBIT_PASS = os.getenv("RABBIT_PASS", "guest")
RABBIT_VHOST = os.getenv("RABBIT_VHOST", "/")
EXCHANGE = os.getenv("RABBIT_EXCHANGE", "logs")
RABBIT_QUEUE = os.getenv("RABBIT_QUEUE", "moteur_correlation")

ZONES = [
    {"name": "Paris", "lat": 48.8566, "lon": 2.3522},
]

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_POLLUTION_FIELDS = [
    "city",
    "zone",
    "pollutant",
    "value",
    "unit",
    "latitude",
    "longitude",
    "timestamp",
]

DEFAULT_TRAFFIC_FIELDS = [
    "city",
    "zone",
    "street",
    "section_id",
    "q",
    "etat_trafic",
    "latitude",
    "longitude",
    "timestamp",
    "upstream_name",
    "downstream_name",
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