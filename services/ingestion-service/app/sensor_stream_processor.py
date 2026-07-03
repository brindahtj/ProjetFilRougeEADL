import logging
import re
from typing import Dict

import requests

from .exceptions import InvalidSensorIdError, MetricValidationError
from .sensor import Sensor
from .sensor_state import SensorStatus

log = logging.getLogger("sensor_stream_processor")


class SensorStreamProcessor:
    """Orchestre le traitement du flux de métriques d'un capteur.

    Ce processor ne réimplémente AUCUNE règle de validation métier
    (complétude, plages de valeurs) : c'est `validation-service` qui est
    l'unique autorité sur ce sujet. Le rôle de `SensorStreamProcessor` se
    limite à :
    - vérifier la forme de `sensor_id` (propre à cette route, → HTTP 400),
    - transmettre chaque métrique à `validation-service`,
    - interpréter sa réponse pour mettre à jour l'état du capteur (pattern
      State) : une métrique jugée **aberrante** par validation-service fait
      transitionner le capteur vers WARNING/CRITICAL ; une métrique
      **incomplète** est simplement rejetée, sans impacter l'état du
      capteur (on ne peut rien conclure d'une donnée qu'on ne peut pas
      interpréter).
    """

    SENSOR_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,64}$")

    def __init__(self, validation_service_url: str, sensors: Dict[str, Sensor] | None = None):
        self._validation_service_url = validation_service_url.rstrip("/")
        self._sensors: Dict[str, Sensor] = sensors if sensors is not None else {}

    def process(self, sensor_id: str, metrics: list) -> dict:
        """Traite un lot de métriques pour un capteur.

        Raises:
            InvalidSensorIdError: `sensor_id` malformé (→ HTTP 400).
            MetricValidationError: lot de métriques vide (→ HTTP 422).
        """
        self._validate_sensor_id(sensor_id)

        if not metrics:
            raise MetricValidationError("metrics list must not be empty")

        sensor = self._sensors.setdefault(
            sensor_id, Sensor(sensor_id=sensor_id, sensor_type=metrics[0].type)
        )

        details = []
        accepted = 0
        rejected = 0

        for metric in metrics:
            outcome = self._submit_to_validation_service(sensor_id, metric)

            if outcome["valid"]:
                # Donnée conforme : lecture normale, publiée par validation-service.
                new_status = sensor.update(
                    value=metric.value if metric.type == "pollution" else metric.q,
                    unit=metric.pollutant if metric.type == "pollution" else "q",
                    timestamp=metric.timestamp,
                    is_anomaly=False,
                )
                accepted += 1
                details.append(
                    {
                        "type": metric.type,
                        "published": True,
                        "anomaly": False,
                        "error": None,
                    }
                )
            elif outcome["aberrant"]:
                # Donnée interprétable mais physiquement implausible : pas
                # publiée par validation-service, mais on capitalise
                # l'information en la faisant remonter dans l'état du capteur.
                new_status = sensor.update(
                    value=metric.value if metric.type == "pollution" else metric.q,
                    unit=metric.pollutant if metric.type == "pollution" else "q",
                    timestamp=metric.timestamp,
                    is_anomaly=True,
                )
                rejected += 1
                details.append(
                    {
                        "type": metric.type,
                        "published": False,
                        "anomaly": True,
                        "error": "; ".join(outcome["errors"]) or "aberrant value",
                    }
                )
                log.warning(
                    "⚠ Donnée aberrante pour %s : capteur désormais %s", sensor_id, new_status.value
                )
            else:
                # Donnée incomplète : impossible à interpréter, on ne touche
                # pas à l'état du capteur.
                rejected += 1
                details.append(
                    {
                        "type": metric.type,
                        "published": False,
                        "anomaly": False,
                        "error": "; ".join(outcome["errors"]) or "incomplete data",
                    }
                )
                log.warning("✗ Donnée incomplète pour %s : %s", sensor_id, outcome["errors"])

        return {
            "sensor_id": sensor_id,
            "sensor_status": sensor.status.value,
            "total": len(metrics),
            "accepted": accepted,
            "rejected": rejected,
            "details": details,
        }

    def _validate_sensor_id(self, sensor_id: str) -> None:
        if not sensor_id or not self.SENSOR_ID_PATTERN.match(sensor_id):
            raise InvalidSensorIdError(
                f"invalid sensor_id format: '{sensor_id}' "
                "(expected 3-64 alphanumeric characters, '_' or '-')"
            )

    def _submit_to_validation_service(self, sensor_id: str, metric) -> dict:
        """Transmet une métrique à validation-service et normalise sa réponse.

        En cas d'échec réseau (service injoignable), on considère la
        métrique comme non publiée mais on ne fait pas planter toute la
        requête : elle est reportée comme rejetée avec l'erreur réseau,
        sans impacter l'état du capteur (on ne peut rien en conclure)."""
        try:
            resp = requests.post(
                f"{self._validation_service_url}/validate",
                params={"sensor_id": sensor_id},
                json=metric.model_dump(mode="json"),
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "valid": data.get("valid", False),
                "aberrant": data.get("aberrant", False),
                "errors": data.get("errors", []),
            }
        except requests.RequestException as exc:
            log.error("validation-service unreachable for sensor %s: %s", sensor_id, exc)
            return {"valid": False, "aberrant": False, "errors": [f"validation-service unreachable: {exc}"]}

    def get_sensor_status(self, sensor_id: str) -> SensorStatus:
        sensor = self._sensors.get(sensor_id)
        return sensor.status if sensor else SensorStatus.NORMAL

    def get_critical_sensors(self) -> Dict[str, Sensor]:
        return {
            sid: s for sid, s in self._sensors.items() if s.status == SensorStatus.CRITICAL
        }
