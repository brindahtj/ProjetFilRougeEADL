import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any

from Api_ingestion.config import (
    TRAFFIC_API_KEY,
    HERE_TRAFFIC_URL,
    OPENAQ_BASE_URL,
    ZONES,
)
from Api_ingestion.constants import (
    ALLOWED_POLLUTANTS,
    MIN_ANOMALIES_CRITICAL,
    MIN_ANOMALIES_WARNING,
)
from Api_ingestion.domain import PollutionReading, TrafficReading
from Api_ingestion.exceptions import ApiClientError, DataValidationError
from Api_ingestion.http_client import HttpClient

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Interface abstraite
# ─────────────────────────────────────────────────────────────────────────────


class DataSourceClient(ABC):
    """Interface pour tous les clients de source de données."""

    @abstractmethod
    def extract_readings(self) -> List:
        """Extrait les lectures de la source de données."""
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────────
# Parseurs de données
# ─────────────────────────────────────────────────────────────────────────────


class PollutionDataParser:
    """Responsable du parsing de données de pollution OpenAQ."""

    @staticmethod
    def extract_pollutant_value(sensor: Dict[str, Any]) -> tuple:
        """
        Extrait polluant et valeur d'un capteur.

        Returns:
            tuple: (pollutant, value, unit, timestamp)
        """
        parameter = (
            sensor.get("parameter")
            or sensor.get("name")
            or sensor.get("parameterName")
        )
        pollutant = None
        if isinstance(parameter, str):
            pollutant = parameter
        elif isinstance(parameter, dict):
            pollutant = parameter.get("name")

        latest = (
            sensor.get("lastValue")
            or sensor.get("latest")
            or sensor.get("value")
            or sensor.get("latestMeasurement")
        )
        value = None
        timestamp = None

        if isinstance(latest, dict):
            value = latest.get("value")
            timestamp = latest.get("datetime") or latest.get("date")
        else:
            value = latest

        unit = sensor.get("unit") or (
            sensor.get("units") if isinstance(sensor.get("units"), str) else None
        )

        return pollutant, value, unit, timestamp

    @staticmethod
    def is_valid_pollutant(pollutant: str) -> bool:
        """Vérifie si le polluant est autorisé."""
        return pollutant and pollutant.lower() in ALLOWED_POLLUTANTS


# ─────────────────────────────────────────────────────────────────────────────
# Clients API
# ─────────────────────────────────────────────────────────────────────────────


class OpenAQClient(DataSourceClient):
    """
    Client pour l'API OpenAQ.

    Récupère les mesures de pollution pour les villes configurées.
    """

    def __init__(
        self,
        base_url: str = OPENAQ_BASE_URL,
        country: str = "FR",
        limit: int = 100,
        timeout: int = 10,
    ):
        """
        Args:
            base_url: URL de base de l'API OpenAQ
            country: Code pays ISO (ex: "FR")
            limit: Nombre max de locations par requête
            timeout: Timeout en secondes
        """
        self.country = country
        self.limit = limit
        self.http_client = HttpClient(base_url, timeout=timeout)
        self.parser = PollutionDataParser()

    def extract_readings(self) -> List[PollutionReading]:
        """
        Récupère et parse les mesures de pollution.

        Returns:
            Liste des lectures de pollution
        """
        try:
            data = self._fetch_locations()
            if not data:
                log.info("Aucune donnée pollution reçue")
                return []

            readings = []
            for location in data.get("results", []):
                readings.extend(self._extract_location_readings(location))

            log.info(f"✅ {len(readings)} mesures pollution extraites")
            return readings
        except ApiClientError:
            raise
        except Exception as exc:
            raise ApiClientError(
                f"Erreur OpenAQ inattendue : {exc}",
                context="OPENAQ_EXTRACT",
            ) from exc

    def _fetch_locations(self) -> Dict[str, Any]:
        """Récupère les locations depuis OpenAQ."""
        return self.http_client.get(
            endpoint="/locations",
            params={"country": self.country, "limit": self.limit},
            error_message="Erreur OpenAQ",
        )

    def _extract_location_readings(
        self, location: Dict[str, Any]
    ) -> List[PollutionReading]:
        """Extrait les lectures d'une location."""
        readings = []

        # Récupère les coordonnées
        coordinates = location.get("coordinates") or {}
        latitude = coordinates.get("latitude") or 0.0
        longitude = coordinates.get("longitude") or 0.0
        city = location.get("city", "Unknown")

        # Récupère les capteurs (structure varie selon l'API)
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

            try:
                reading = self._build_pollution_reading(
                    sensor, city, latitude, longitude
                )
                if reading:
                    readings.append(reading)
            except DataValidationError as exc:
                log.warning(f"Capteur ignoré : {exc}")
                continue

        return readings

    def _build_pollution_reading(
        self,
        sensor: Dict[str, Any],
        city: str,
        latitude: float,
        longitude: float,
    ) -> Optional[PollutionReading]:
        """Construit une PollutionReading valide."""
        pollutant, value, unit, timestamp = self.parser.extract_pollutant_value(
            sensor
        )

        if not self.parser.is_valid_pollutant(pollutant):
            raise DataValidationError(
                f"Polluant invalide ou absent : {pollutant}"
            )

        if value is None:
            raise DataValidationError("Valeur manquante")

        try:
            return PollutionReading(
                city=city,
                pollutant=pollutant,
                value=float(value),
                unit=unit or "",
                latitude=float(latitude),
                longitude=float(longitude),
                timestamp=timestamp or datetime.utcnow().isoformat(),
            )
        except (TypeError, ValueError) as exc:
            raise DataValidationError(f"Conversion de type échouée : {exc}") from exc


class HereTrafficClient(DataSourceClient):
    """
    Client pour l'API HERE Traffic.

    Récupère les données de trafic pour les zones configurées.
    """

    def __init__(
        self,
        base_url: str = HERE_TRAFFIC_URL,
        api_key: str = TRAFFIC_API_KEY,
        timeout: int = 10,
    ):
        """
        Args:
            base_url: URL de base de l'API HERE
            api_key: Clé API HERE
            timeout: Timeout en secondes
        """
        self.api_key = api_key
        self.http_client = HttpClient(base_url, timeout=timeout)

    def extract_readings(self) -> List[TrafficReading]:
        """
        Récupère et parse les données de trafic.

        Returns:
            Liste des lectures de trafic
        """
        readings = []

        for zone in ZONES:
            try:
                data = self._fetch_flow(zone["lat"], zone["lon"])
                if data:
                    zone_readings = self._extract_zone_readings(data, zone)
                    readings.extend(zone_readings)
            except ApiClientError as exc:
                log.warning(f"Zone {zone['name']} ignorée : {exc}")
                continue

        log.info(f"✅ {len(readings)} mesures trafic extraites")
        return readings

    def _fetch_flow(self, lat: float, lon: float) -> Dict[str, Any]:
        """Récupère le flux de trafic pour une position."""
        return self.http_client.get(
            endpoint="",
            params={
                "in": f"circle:{lat},{lon};r=5000",
                "locationReferencing": "shape",
                "apiKey": self.api_key,
            },
            error_message=f"Erreur HERE API ({lat}, {lon})",
        )

    def _extract_zone_readings(
        self, data: Dict[str, Any], zone: Dict[str, Any]
    ) -> List[TrafficReading]:
        """Extrait les lectures de trafic pour une zone."""
        readings = []

        for item in data.get("results", []) or []:
            try:
                reading = self._build_traffic_reading(item, zone)
                if reading:
                    readings.append(reading)
            except DataValidationError as exc:
                log.debug(f"Donnée trafic ignorée : {exc}")
                continue

        return readings

    def _build_traffic_reading(
        self, item: Dict[str, Any], zone: Dict[str, Any]
    ) -> Optional[TrafficReading]:
        """Construit une TrafficReading valide."""
        current_flow = item.get("currentFlow", {}) or {}

        try:
            return TrafficReading(
                city=zone["name"],
                jam_factor=float(current_flow.get("jamFactor", 0) or 0),
                current_speed=float(current_flow.get("speed", 0) or 0),
                free_flow_speed=float(current_flow.get("freeFlowSpeed", 0) or 0),
                confidence=float(current_flow.get("confidence", 0) or 0),
                latitude=float(zone["lat"]),
                longitude=float(zone["lon"]),
                timestamp=datetime.utcnow().isoformat(),
            )
        except (TypeError, ValueError) as exc:
            raise DataValidationError(f"Conversion de type échouée : {exc}") from exc