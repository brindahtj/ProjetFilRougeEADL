import requests
import logging
from typing import Dict, Optional
import json

log = logging.getLogger("ingestion")

class ThresholdCache:
    def __init__(self, referential_url: str = "http://referential:8001"):
        self.referential_url = referential_url
        self.cache: Dict = {}
        self.load()

    def load(self):
        """Charge les seuils depuis le service referential."""
        try:
            resp = requests.get(f"{self.referential_url}/thresholds")
            resp.raise_for_status()
            thresholds = resp.json()
            # Transform list to dict: {key: value}
            self.cache = {t["key"]: t["value"] for t in thresholds}
            log.info("Loaded %d thresholds", len(self.cache))
        except Exception as exc:
            log.error("Failed to load thresholds: %s", exc)
            # fallback to defaults
            self.cache = {
                "NO2_WARNING": 100,
                "NO2_CRITICAL": 200,
                "TRAFFIC_Q_WARNING": 500,
                "TRAFFIC_Q_CRITICAL": 800,
            }

    def get(self, key: str, default=None):
        return self.cache.get(key, default)

# Global instance
thresholds = None

def init_thresholds(referential_url: str = "http://referential:8001"):
    global thresholds
    thresholds = ThresholdCache(referential_url)

def get_threshold(key: str, default=None):
    global thresholds
    if thresholds is None:
        init_thresholds()
    return thresholds.get(key, default)