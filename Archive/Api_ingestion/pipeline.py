import logging
import time

from Archive.Api_ingestion.api_clients import ParisTrafficClient, OpenAQClient
from Archive.Api_ingestion.config import (
    DEFAULT_POLLUTION_FIELDS,
    DEFAULT_TRAFFIC_FIELDS,
    LOG_DIR,
    OUTPUT_DIR,
    setup_logging,
)
from Archive.Api_ingestion.constants import (
    ROUTING_KEY_ALERTS,
)
from Archive.Api_ingestion.csv_repository import CsvRepository
from Archive.Api_ingestion.domain import TrafficReading, PollutionReading
from Archive.Api_ingestion.exceptions import SmartCityException
from Archive.Api_ingestion.publisher import RabbitMQPublisher

log = logging.getLogger(__name__)


class SmartCityPipeline:
    def __init__(
        self,
        pollution_client=None,
        traffic_client=None,
        pollution_repository=None,
        traffic_repository=None,
        publisher=None,
        sleep_fn=time.sleep,
    ):
        setup_logging(LOG_DIR)
        self.pollution_client = pollution_client or OpenAQClient()
        self.traffic_client = traffic_client or ParisTrafficClient()
        self.pollution_repository = pollution_repository or CsvRepository(
            OUTPUT_DIR / "pollution.csv", DEFAULT_POLLUTION_FIELDS
        )
        self.traffic_repository = traffic_repository or CsvRepository(
            OUTPUT_DIR / "traffic.csv", DEFAULT_TRAFFIC_FIELDS
        )
        self.publisher = publisher or RabbitMQPublisher()
        self.sleep_fn = sleep_fn
        self.traffic_history = []

    def run(self, n_cycles=5, interval_sec=60):
        log.info("🚀 SMART CITY PIPELINE")

        for cycle in range(1, n_cycles + 1):
            try:
                log.info("Cycle %d/%d", cycle, n_cycles)

                pollution = self.pollution_client.extract_readings()
                traffic = self.traffic_client.extract_readings()

                # Traiter pollution
                if pollution:
                    self.pollution_repository.append(pollution)
                    self.publisher.publish(
                        [reading.__dict__ for reading in pollution],
                        routing_key="pollution",
                    )
                    # après avoir traité pollution (dans if pollution:)
                    self.pollution_history.extend(pollution)
                    if len(self.pollution_history) > 2000:
                        self.pollution_history = self.pollution_history[-2000:]


                    log.info("✅ %d mesures pollution publiées", len(pollution))

                    # Détecter alertes pollution
                    alerts = self._detect_pollution_alerts(pollution)
                    for alert in alerts:
                        self.publisher.publish(alert, routing_key=ROUTING_KEY_ALERTS)
                        log.warning("🚨 Alerte pollution : %s", alert)

                # Traiter trafic
                if traffic:
                    self.traffic_repository.append(traffic)
                    self.publisher.publish(
                        [reading.__dict__ for reading in traffic],
                        routing_key="traffic",
                    )
                    # après avoir traité traffic (dans if traffic:)
                    self.traffic_history.extend(traffic)
                    if len(self.traffic_history) > 2000:
                        self.traffic_history = self.traffic_history[-2000:]
                    log.info("✅ %d mesures trafic publiées", len(traffic))

                    # Accumuler historique
                    self.traffic_history.extend(traffic)
                    # Garder seulement les 1000 dernières mesures
                    if len(self.traffic_history) > 1000:
                        self.traffic_history = self.traffic_history[-1000:]

                    # Détecter alertes trafic
                    alerts = self._detect_traffic_alerts(traffic)
                    for alert in alerts:
                        self.publisher.publish(alert, routing_key=ROUTING_KEY_ALERTS)
                        log.warning("🚨 Alerte trafic : %s", alert)

            except SmartCityException as exc:
                log.error("Erreur métier : %s", exc)
            except Exception as exc:
                log.exception("Erreur inattendue : %s", exc)

            if cycle < n_cycles:
                self.sleep_fn(interval_sec)

        log.info("🏁 Pipeline terminé")

from statistics import mean, stdev
from Archive.Api_ingestion.constants import (
    TRAFFIC_Q_FIXED_WARNING,
    TRAFFIC_Q_FIXED_CRITICAL,
    TRAFFIC_ABOVE_MEAN_FACTOR,
    TRAFFIC_ABOVE_MEAN_STD_MULT,
    POLLUTION_ABOVE_MEAN_FACTOR,
    POLLUTION_ABOVE_MEAN_STD_MULT,
    HISTORY_MIN_FOR_STATS,
    NO2_WARNING,
    NO2_CRITICAL,
)

def _detect_traffic_alerts(self, current_readings: list) -> list:
    """Détecte les alertes trafic basées sur moyenne+facteur, std, et seuils fixes/percentiles."""
    alerts = []

    for reading in current_readings:
        section_history = [r for r in self.traffic_history if r.section_id == reading.section_id]
        q_values = [r.q for r in section_history]

        # Si on a assez d'historique pour stats
        if len(q_values) >= HISTORY_MIN_FOR_STATS:
            avg_q = mean(q_values)
            try:
                sd_q = stdev(q_values)
            except Exception:
                sd_q = 0.0

            # règle 1 : au-dessus de la moyenne * facteur
            above_factor = reading.q >= avg_q * TRAFFIC_ABOVE_MEAN_FACTOR
            # règle 2 : au-dessus de mean + k * std
            above_std = sd_q > 0 and reading.q >= avg_q + TRAFFIC_ABOVE_MEAN_STD_MULT * sd_q

            if above_factor or above_std:
                # définir niveau : CRITICAL si très au-dessus (ex: > mean + 2*std) sinon WARNING
                level = "CRITICAL" if (sd_q and reading.q >= avg_q + 2 * sd_q) else "WARNING"
                alerts.append({
                    "type": "traffic",
                    "level": level,
                    "street": reading.street,
                    "section_id": reading.section_id,
                    "q": reading.q,
                    "q_avg": round(avg_q, 2),
                    "q_std": round(sd_q, 2),
                    "reason": "above_mean",
                    "timestamp": reading.timestamp,
                })
                # skip other checks for this reading
                continue

        # Si pas assez d'historique ou pas déclenché ci‑dessus, retomber sur seuils fixes
        if reading.q >= TRAFFIC_Q_FIXED_CRITICAL:
            alerts.append({
                "type": "traffic",
                "level": "CRITICAL",
                "street": reading.street,
                "section_id": reading.section_id,
                "q": reading.q,
                "reason": "fixed_threshold",
                "timestamp": reading.timestamp,
            })
        elif reading.q >= TRAFFIC_Q_FIXED_WARNING:
            alerts.append({
                "type": "traffic",
                "level": "WARNING",
                "street": reading.street,
                "section_id": reading.section_id,
                "q": reading.q,
                "reason": "fixed_threshold",
                "timestamp": reading.timestamp,
            })

    return alerts


def _detect_pollution_alerts(self, readings: list) -> list:
    """Détecte alertes pollution NO2 basées sur moyenne+facteur/std et seuils fixes."""
    alerts = []

    for reading in readings:
        if reading.pollutant.lower() != "no2":
            # pour l'instant on n'applique la règle moyenne qu'à NO2 (vous pouvez étendre)
            if reading.value >= NO2_CRITICAL:
                alerts.append({
                    "type": "pollution",
                    "level": "CRITICAL",
                    "pollutant": reading.pollutant,
                    "city": reading.city,
                    "zone": getattr(reading, "zone", None),
                    "value": reading.value,
                    "reason": "fixed_threshold",
                    "timestamp": reading.timestamp,
                })
            elif reading.value >= NO2_WARNING:
                alerts.append({
                    "type": "pollution",
                    "level": "WARNING",
                    "pollutant": reading.pollutant,
                    "city": reading.city,
                    "zone": getattr(reading, "zone", None),
                    "value": reading.value,
                    "reason": "fixed_threshold",
                    "timestamp": reading.timestamp,
                })
            continue

        # historique pollution pour même city+zone (ou sensor si vous avez id)
        hist = [
            r.value for r in getattr(self, "pollution_history", [])
            if r.city == reading.city and getattr(r, "zone", None) == getattr(reading, "zone", None) and r.pollutant.lower() == "no2"
        ]

        if len(hist) >= HISTORY_MIN_FOR_STATS:
            avg_v = mean(hist)
            try:
                sd_v = stdev(hist)
            except Exception:
                sd_v = 0.0

            above_factor = reading.value >= avg_v * POLLUTION_ABOVE_MEAN_FACTOR
            above_std = sd_v > 0 and reading.value >= avg_v + POLLUTION_ABOVE_MEAN_STD_MULT * sd_v

            if above_factor or above_std:
                level = "CRITICAL" if (sd_v and reading.value >= avg_v + 2 * sd_v) else "WARNING"
                alerts.append({
                    "type": "pollution",
                    "level": level,
                    "pollutant": "NO2",
                    "city": reading.city,
                    "zone": getattr(reading, "zone", None),
                    "value": reading.value,
                    "value_avg": round(avg_v, 2),
                    "value_std": round(sd_v, 2),
                    "reason": "above_mean",
                    "timestamp": reading.timestamp,
                })
                continue

        # retomber sur seuils fixes si pas d'historique suffisant
        if reading.value >= NO2_CRITICAL:
            alerts.append({
                "type": "pollution",
                "level": "CRITICAL",
                "pollutant": "NO2",
                "city": reading.city,
                "zone": getattr(reading, "zone", None),
                "value": reading.value,
                "reason": "fixed_threshold",
                "timestamp": reading.timestamp,
            })
        elif reading.value >= NO2_WARNING:
            alerts.append({
                "type": "pollution",
                "level": "WARNING",
                "pollutant": "NO2",
                "city": reading.city,
                "zone": getattr(reading, "zone", None),
                "value": reading.value,
                "reason": "fixed_threshold",
                "timestamp": reading.timestamp,
            })

    return alerts

def run_pipeline(n_cycles=5, interval_sec=60):
    SmartCityPipeline().run(n_cycles=n_cycles, interval_sec=interval_sec)