import logging
import time
from statistics import mean

from Api_ingestion.api_clients import ParisTrafficClient, OpenAQClient
from Api_ingestion.config import (
    DEFAULT_POLLUTION_FIELDS,
    DEFAULT_TRAFFIC_FIELDS,
    LOG_DIR,
    OUTPUT_DIR,
    setup_logging,
)
from Api_ingestion.constants import (
    TRAFFIC_Q_FIXED_WARNING,
    TRAFFIC_Q_FIXED_CRITICAL,
    TRAFFIC_Q_PERCENTILE_WARNING,
    TRAFFIC_Q_PERCENTILE_CRITICAL,
    TRAFFIC_HISTORY_MIN_SIZE,
    NO2_WARNING,
    NO2_CRITICAL,
    ROUTING_KEY_ALERTS,
)
from Api_ingestion.csv_repository import CsvRepository
from Api_ingestion.domain import TrafficReading, PollutionReading
from Api_ingestion.exceptions import SmartCityException
from Api_ingestion.publisher import RabbitMQPublisher

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

    def _detect_pollution_alerts(self, readings: list) -> list:
        """Détecte les alertes pollution (NO2)."""
        alerts = []
        for reading in readings:
            if reading.pollutant.lower() == "no2":
                if reading.value >= NO2_CRITICAL:
                    alerts.append(
                        {
                            "type": "pollution",
                            "level": "CRITICAL",
                            "pollutant": "NO2",
                            "city": reading.city,
                            "value": reading.value,
                            "unit": reading.unit,
                            "timestamp": reading.timestamp,
                        }
                    )
                elif reading.value >= NO2_WARNING:
                    alerts.append(
                        {
                            "type": "pollution",
                            "level": "WARNING",
                            "pollutant": "NO2",
                            "city": reading.city,
                            "value": reading.value,
                            "unit": reading.unit,
                            "timestamp": reading.timestamp,
                        }
                    )
        return alerts

    def _detect_traffic_alerts(self, current_readings: list) -> list:
        """Détecte les alertes trafic basées sur percentile et seuil fixe."""
        alerts = []

        for reading in current_readings:
            # Récupérer l'historique pour ce tronçon
            section_history = [
                r for r in self.traffic_history if r.section_id == reading.section_id
            ]

            if len(section_history) < TRAFFIC_HISTORY_MIN_SIZE:
                # Pas assez de données historiques, utiliser seuil fixe
                if reading.q >= TRAFFIC_Q_FIXED_CRITICAL:
                    alerts.append(
                        {
                            "type": "traffic",
                            "level": "CRITICAL",
                            "street": reading.street,
                            "section_id": reading.section_id,
                            "q": reading.q,
                            "reason": "seuil_fixe",
                            "timestamp": reading.timestamp,
                        }
                    )
                elif reading.q >= TRAFFIC_Q_FIXED_WARNING:
                    alerts.append(
                        {
                            "type": "traffic",
                            "level": "WARNING",
                            "street": reading.street,
                            "section_id": reading.section_id,
                            "q": reading.q,
                            "reason": "seuil_fixe",
                            "timestamp": reading.timestamp,
                        }
                    )
            else:
                # Calculer percentiles
                q_values = sorted([r.q for r in section_history])
                avg_q = mean(q_values)

                p80_idx = int(len(q_values) * TRAFFIC_Q_PERCENTILE_WARNING)
                p90_idx = int(len(q_values) * TRAFFIC_Q_PERCENTILE_CRITICAL)

                p80 = q_values[min(p80_idx, len(q_values) - 1)]
                p90 = q_values[min(p90_idx, len(q_values) - 1)]

                # Comparer mesure actuelle
                if reading.q >= p90 or reading.q >= TRAFFIC_Q_FIXED_CRITICAL:
                    alerts.append(
                        {
                            "type": "traffic",
                            "level": "CRITICAL",
                            "street": reading.street,
                            "section_id": reading.section_id,
                            "q": reading.q,
                            "q_avg": round(avg_q, 2),
                            "p80": round(p80, 2),
                            "p90": round(p90, 2),
                            "reason": "percentile_90"
                            if reading.q >= p90
                            else "seuil_fixe",
                            "timestamp": reading.timestamp,
                        }
                    )
                elif reading.q >= p80 or reading.q >= TRAFFIC_Q_FIXED_WARNING:
                    alerts.append(
                        {
                            "type": "traffic",
                            "level": "WARNING",
                            "street": reading.street,
                            "section_id": reading.section_id,
                            "q": reading.q,
                            "q_avg": round(avg_q, 2),
                            "p80": round(p80, 2),
                            "p90": round(p90, 2),
                            "reason": "percentile_80"
                            if reading.q >= p80
                            else "seuil_fixe",
                            "timestamp": reading.timestamp,
                        }
                    )

        return alerts


def run_pipeline(n_cycles=5, interval_sec=60):
    SmartCityPipeline().run(n_cycles=n_cycles, interval_sec=interval_sec)