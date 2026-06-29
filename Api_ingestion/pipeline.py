import logging
import time

from Api_ingestion.api_clients import HereTrafficClient, OpenAQClient
from Api_ingestion.config import DEFAULT_POLLUTION_FIELDS, DEFAULT_TRAFFIC_FIELDS, LOG_DIR, OUTPUT_DIR, setup_logging
from Api_ingestion.csv_repository import CsvRepository
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
        self.traffic_client = traffic_client or HereTrafficClient()
        self.pollution_repository = pollution_repository or CsvRepository(
            OUTPUT_DIR / "pollution.csv", DEFAULT_POLLUTION_FIELDS
        )
        self.traffic_repository = traffic_repository or CsvRepository(
            OUTPUT_DIR / "traffic.csv", DEFAULT_TRAFFIC_FIELDS
        )
        self.publisher = publisher or RabbitMQPublisher()
        self.sleep_fn = sleep_fn

    def run(self, n_cycles=5, interval_sec=60):
        log.info("🚀 SMART CITY PIPELINE")

        for cycle in range(1, n_cycles + 1):
            try:
                log.info("Cycle %d/%d", cycle, n_cycles)

                pollution = self.pollution_client.extract_readings()
                traffic = self.traffic_client.extract_readings()

                if pollution:
                    self.pollution_repository.append(pollution)
                    self.publisher.publish([reading.__dict__ for reading in pollution], routing_key="pollution")
                    log.info("✅ %d mesures pollution publiées", len(pollution))

                if traffic:
                    self.traffic_repository.append(traffic, transform=self._normalize_traffic_row)
                    self.publisher.publish([reading.__dict__ for reading in traffic], routing_key="traffic")
                    log.info("✅ %d mesures trafic publiées", len(traffic))

            except SmartCityException as exc:
                log.error("Erreur métier : %s", exc)
            except Exception as exc:
                log.exception("Erreur inattendue : %s", exc)

            if cycle < n_cycles:
                self.sleep_fn(interval_sec)

        log.info("🏁 Pipeline terminé")

    @staticmethod
    def _normalize_traffic_row(row):
        if "jamFactor" in row and "jam_factor" not in row:
            row["jam_factor"] = row.pop("jamFactor")
        return row


def run_pipeline(n_cycles=5, interval_sec=60):
    SmartCityPipeline().run(n_cycles=n_cycles, interval_sec=interval_sec)