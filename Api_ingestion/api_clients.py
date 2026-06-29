import logging
import requests
from datetime import datetime
from abc import ABC, abstractmethod

from Api_ingestion.config import OPENAQ_BASE_URL, HERE_TRAFFIC_URL, HERE_API_KEY, ZONES
from Api_ingestion.domain import PollutionReading, TrafficReading

log = logging.getLogger(__name__)


class DataSourceClient(ABC):
    @abstractmethod
    def extract_readings(self):
        raise NotImplementedError


class OpenAQClient(DataSourceClient):
    ALLOWED_POLLUTANTS = {"no2", "pm25", "pm10", "o3", "co"}

    def __init__(self, base_url=OPENAQ_BASE_URL, country="FR", limit=100, timeout=10):
        self.base_url = base_url
        self.country = country
        self.limit = limit
        self.timeout = timeout

    def fetch_locations(self):
        url = f"{self.base_url}/locations"
        params = {"country": self.country, "limit": self.limit}

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            log.error("Erreur OpenAQ : %s", exc)
            return None

    def extract_readings(self):
        data = self.fetch_locations()
        if not data:
            return []

        readings = []
        for location in data.get("results", []):
            readings.extend(self._extract_location_readings(location))
        return readings

    def _extract_location_readings(self, location):
        readings = []
        coordinates = location.get("coordinates") or {}
        latitude = coordinates.get("latitude") or 0.0
        longitude = coordinates.get("longitude") or 0.0

        sensors = (
            location.get("sensors")
            or location.get("parameters")
            or location.get("latestMeasurements")
            or location.get("measurements")
            or []
        )

        for sensor in sensors:
            if not isinstance(sensor, dict):
                continue

            normalized = self._normalize_sensor(sensor)
            if not normalized:
                continue

            pollutant, value, unit, timestamp = normalized
            if pollutant not in self.ALLOWED_POLLUTANTS or value is None:
                continue

            readings.append(
                PollutionReading(
                    city=location.get("city", "Unknown"),
                    pollutant=pollutant,
                    value=float(value),
                    unit=unit or "",
                    latitude=float(latitude),
                    longitude=float(longitude),
                    timestamp=timestamp or datetime.utcnow().isoformat(),
                )
            )

        return readings

    def _normalize_sensor(self, sensor):
        parameter = sensor.get("parameter") or sensor.get("name") or sensor.get("parameterName")
        pollutant = None
        if isinstance(parameter, str):
            pollutant = parameter
        elif isinstance(parameter, dict):
            pollutant = parameter.get("name")

        latest = sensor.get("lastValue") or sensor.get("latest") or sensor.get("value") or sensor.get("latestMeasurement")
        value = None
        timestamp = None

        if isinstance(latest, dict):
            value = latest.get("value")
            timestamp = latest.get("datetime") or latest.get("date")
        else:
            value = latest

        unit = sensor.get("unit") or (sensor.get("units") if isinstance(sensor.get("units"), str) else None)
        return pollutant, value, unit, timestamp


class HereTrafficClient(DataSourceClient):
    def __init__(self, base_url=HERE_TRAFFIC_URL, api_key=HERE_API_KEY, timeout=10):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout

    def fetch_flow(self, lat, lon):
        params = {
            "in": f"circle:{lat},{lon};r=5000",
            "locationReferencing": "shape",
            "apiKey": self.api_key,
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            log.error("Erreur HERE API : %s", exc)
            return None

    def extract_readings(self):
        readings = []
        for zone in ZONES:
            data = self.fetch_flow(zone["lat"], zone["lon"])
            if not data:
                continue

            for item in data.get("results", []) or []:
                current_flow = item.get("currentFlow", {}) or {}
                try:
                    readings.append(
                        TrafficReading(
                            city=zone["name"],
                            jam_factor=float(current_flow.get("jamFactor", 0) or 0),
                            current_speed=float(current_flow.get("speed", 0) or 0),
                            free_flow_speed=float(current_flow.get("freeFlowSpeed", 0) or 0),
                            confidence=float(current_flow.get("confidence", 0) or 0),
                            latitude=float(zone["lat"]),
                            longitude=float(zone["lon"]),
                            timestamp=datetime.utcnow().isoformat(),
                        )
                    )
                except (TypeError, ValueError):
                    continue

        return readings
