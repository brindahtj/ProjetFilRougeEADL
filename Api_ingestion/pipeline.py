import logging
import time
from typing import Optional, Callable

from Api_ingestion.api_clients import HereTrafficClient, OpenAQClient
from Api_ingestion.config import DEFAULT_POLLUTION_FIELDS, DEFAULT_TRAFFIC_FIELDS, LOG_DIR, OUTPUT_DIR, setup_logging
from Api_ingestion.csv_repository import CsvRepository
from Api_ingestion.exceptions import SmartCityException
from Api_ingestion.publisher import RabbitMQPublisher
from Api_ingestion.sensor_processor import SensorStreamProcessor
from Api_ingestion.ports import ReadingStorage, AlertNotifier

log = logging.getLogger(__name__)


class SmartCityPipeline:
    def __init__(
        self,
        pollution_client: Optional[object] = None,
        traffic_client: Optional[object] = None,
        pollution_repository: Optional[ReadingStorage] = None,
        traffic_repository: Optional[ReadingStorage] = None,
        alert_notifier: Optional[AlertNotifier] = None,
        sensor_processor: Optional[SensorStreamProcessor] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        setup_logging(LOG_DIR)
        self.pollution_client = pollution_client or OpenAQClient()
        self.traffic_client = traffic_client or HereTrafficClient()
        self.pollution_repository = pollution_repository or CsvRepository(
            OUTPUT_DIR / "pollution.csv", DEFAULT_POLLUTION_FIELDS
        )
        self.traffic_repository = traffic_repository or CsvRepository(
            OUTPUT_DIR / "traffic.csv", DEFAULT_TRAFFIC_FIELDS
        )
        self.alert_notifier = alert_notifier or RabbitMQPublisher()
        self.sensor_processor = sensor_processor or SensorStreamProcessor()
        self.sleep_fn = sleep_fn

    def run(self, n_cycles: int = 5, interval_sec: int = 60) -> None:
        log.info("🚀 SMART CITY PIPELINE")

        for cycle in range(1, n_cycles + 1):
            try:
                log.info("Cycle %d/%d", cycle, n_cycles)

                pollution_readings = self.pollution_client.extract_readings()
                traffic_readings = self.traffic_client.extract_readings()

                # Traiter et sauvegarder les lectures de pollution
                if pollution_readings:
                    self.pollution_repository.append(pollution_readings)
                    for reading in pollution_readings:
                        status = self.sensor_processor.process_pollution_reading(reading)
                        log.debug("Capteur pollution %s -> %s", reading.city, status.value)
                    
                    payload = [reading.to_dict() for reading in pollution_readings]
                    self.alert_notifier.notify(payload, routing_key="pollution")
                    log.info("✅ %d mesures pollution publiées", len(pollution_readings))

                # Traiter et sauvegarder les lectures de trafic
                if traffic_readings:
                    self.traffic_repository.append(traffic_readings, transform=self._normalize_traffic_row)
                    for reading in traffic_readings:
                        status = self.sensor_processor.process_traffic_reading(reading)
                        log.debug("Capteur trafic %s -> %s", reading.city, status.value)
                    
                    payload = [reading.to_dict() for reading in traffic_readings]
                    self.alert_notifier.notify(payload, routing_key="traffic")
                    log.info("✅ %d mesures trafic publiées", len(traffic_readings))

                # Publier les alertes critiques
                critical = self.sensor_processor.get_critical_sensors()
                if critical:
                    self.alert_notifier.notify(
                        {sid: s.to_dict() for sid, s in critical.items()},
                        routing_key="critical_alerts",
                    )
                    log.warning("⚠️  %d capteurs en état CRITIQUE", len(critical))

            except SmartCityException as exc:
                log.error("Erreur métier : %s", exc)
            except Exception as exc:
                log.exception("Erreur inattendue : %s", exc)

            if cycle < n_cycles:
                self.sleep_fn(interval_sec)

        log.info("🏁 Pipeline terminé")

    @staticmethod
    def _normalize_traffic_row(row: dict) -> dict:
        if "jamFactor" in row and "jam_factor" not in row:
            row["jam_factor"] = row.pop("jamFactor")
        return row


def run_pipeline(n_cycles: int = 5, interval_sec: int = 60) -> None:
    SmartCityPipeline().run(n_cycles=n_cycles, interval_sec=interval_sec)