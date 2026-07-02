from datetime import datetime, timedelta
from .models import RawMeasurement, ValidationResult
from .config import (
    LATITUDE_MIN, LATITUDE_MAX, LONGITUDE_MIN, LONGITUDE_MAX,
    POLLUTION_ALLOWED, POLLUTION_VALUE_MIN, POLLUTION_VALUE_MAX,
    TRAFFIC_Q_MIN, TRAFFIC_Q_MAX, CITIES_ALLOWED, ZONES_ALLOWED
)
import logging

log = logging.getLogger("validator")

class MeasurementValidator:
    @staticmethod
    def validate(measurement: RawMeasurement) -> ValidationResult:
        """Valide une mesure brute."""
        errors = []
        warnings = []

        # Check type
        if measurement.type not in ["pollution", "traffic"]:
            errors.append(f"Invalid type: {measurement.type}")
            return ValidationResult(
                state="CRITICAL",
                valid=False,
                errors=errors
            )

        # Common validations
        if measurement.city:
            measurement.city = measurement.city.lower()
            if measurement.city not in CITIES_ALLOWED:
                warnings.append(f"City not in whitelist: {measurement.city}")
        else:
            errors.append("city is required")

        if measurement.zone:
            measurement.zone = measurement.zone.lower()
            if measurement.zone not in ZONES_ALLOWED:
                warnings.append(f"Zone not in whitelist: {measurement.zone}")

        if measurement.latitude is not None:
            if not (LATITUDE_MIN <= measurement.latitude <= LATITUDE_MAX):
                errors.append(f"latitude out of range: {measurement.latitude}")
        else:
            errors.append("latitude is required")  # Donnée incomplète

        if measurement.longitude is not None:
            if not (LONGITUDE_MIN <= measurement.longitude <= LONGITUDE_MAX):
                errors.append(f"longitude out of range: {measurement.longitude}")
        else:
            errors.append("longitude is required")  # Donnée incomplète

        # Timestamp validation
        if measurement.timestamp is None:
            measurement.timestamp = datetime.utcnow()
        else:
            now = datetime.utcnow()
            if measurement.timestamp > now + timedelta(minutes=5):
                errors.append("timestamp in the future (> 5 min)")
            if measurement.timestamp < now - timedelta(hours=24):
                warnings.append("timestamp > 24h old")

        # Type-specific validations
        if measurement.type == "pollution":
            errors.extend(MeasurementValidator._validate_pollution(measurement))
        elif measurement.type == "traffic":
            errors.extend(MeasurementValidator._validate_traffic(measurement))

        state = "CRITICAL" if len(errors) > 0 else "NORMAL"
        valid = state == "NORMAL"
        if valid:
            log.info("✓ [NORMAL] Measurement validated: %s from %s",
                     measurement.type, measurement.city)
        else:
            log.warning("✗ [CRITICAL] Validation failed: %s", errors)

        return ValidationResult(
            state=state,
            valid=valid,
            measurement=measurement if valid else None,
            errors=errors,
            warnings=warnings
        )

    @staticmethod
    def _validate_pollution(m: RawMeasurement) -> list[str]:
        errors = []
        if not m.pollutant:
            errors.append("pollutant is required for pollution")
        elif m.pollutant.lower() not in POLLUTION_ALLOWED:
            errors.append(f"pollutant not allowed: {m.pollutant}")

        if m.value is None:
            errors.append("value is required for pollution")
        elif not (POLLUTION_VALUE_MIN <= m.value <= POLLUTION_VALUE_MAX):
            errors.append(f"value out of range: {m.value}")

        return errors

    @staticmethod
    def _validate_traffic(m: RawMeasurement) -> list[str]:
        errors = []
        if not m.street:
            errors.append("street is required for traffic")
        if not m.section_id:
            errors.append("section_id is required for traffic")
        if m.q is None:
            errors.append("q (traffic metric) is required for traffic")
        elif not (TRAFFIC_Q_MIN <= m.q <= TRAFFIC_Q_MAX):
            errors.append(f"q out of range: {m.q}")

        return errors