from datetime import datetime, timedelta, timezone
from .models import RawMeasurement, ValidationResult
from .state import MeasurementStateMachine
from .config import (
    LATITUDE_MIN, LATITUDE_MAX, LONGITUDE_MIN, LONGITUDE_MAX,
    POLLUTION_ALLOWED, POLLUTION_VALUE_MIN, POLLUTION_VALUE_MAX,
    TRAFFIC_Q_MIN, TRAFFIC_Q_MAX, CITIES_ALLOWED, ZONES_ALLOWED
)
import logging

log = logging.getLogger("validator")


class MeasurementValidator:
    """Validateur encapsulé pour mesures brutes."""

    @staticmethod
    def validate(measurement: RawMeasurement) -> ValidationResult:
        """Valide une mesure brute et détermine son état."""
        state_machine = MeasurementStateMachine()

        MeasurementValidator._validate_type(measurement, state_machine)
        MeasurementValidator._validate_common(measurement, state_machine)
        MeasurementValidator._validate_timestamp(measurement, state_machine)
        MeasurementValidator._validate_type_specific(measurement, state_machine)

        return MeasurementValidator._build_result(measurement, state_machine)

    @staticmethod
    def _validate_type(
        measurement: RawMeasurement, state_machine: MeasurementStateMachine
    ) -> None:
        """Valide le type de mesure."""
        if measurement.type not in ["pollution", "traffic"]:
            state_machine.add_error(f"Invalid type: {measurement.type}")

    @staticmethod
    def _validate_common(
        measurement: RawMeasurement, state_machine: MeasurementStateMachine
    ) -> None:
        """Validations communes à tous les types de mesures."""
        if measurement.city:
            measurement.city = measurement.city.lower()
            if measurement.city not in CITIES_ALLOWED:
                state_machine.add_warning(f"City not in whitelist: {measurement.city}")
        else:
            state_machine.add_error("city is required")

        if measurement.zone:
            measurement.zone = measurement.zone.lower()
            if measurement.zone not in ZONES_ALLOWED:
                state_machine.add_warning(f"Zone not in whitelist: {measurement.zone}")

        if measurement.latitude is not None:
            if not (LATITUDE_MIN <= measurement.latitude <= LATITUDE_MAX):
                state_machine.add_error(f"latitude out of range: {measurement.latitude}")
        else:
            state_machine.add_error("latitude is required")

        if measurement.longitude is not None:
            if not (LONGITUDE_MIN <= measurement.longitude <= LONGITUDE_MAX):
                state_machine.add_error(f"longitude out of range: {measurement.longitude}")
        else:
            state_machine.add_error("longitude is required")

    @staticmethod
    def _validate_timestamp(
        measurement: RawMeasurement, state_machine: MeasurementStateMachine
    ) -> None:
        """Valide le timestamp."""
        if measurement.timestamp is None:
            # Utiliser UTC timezone-aware (Pydantic v2)
            measurement.timestamp = datetime.now(timezone.utc)
        else:
            now = datetime.now(timezone.utc)
            if measurement.timestamp > now + timedelta(minutes=5):
                state_machine.add_error("timestamp in the future (> 5 min)")
            if measurement.timestamp < now - timedelta(hours=24):
                state_machine.add_warning("timestamp > 24h old")

    @staticmethod
    def _validate_type_specific(
        measurement: RawMeasurement, state_machine: MeasurementStateMachine
    ) -> None:
        """Valide les champs spécifiques au type de mesure."""
        if measurement.type == "pollution":
            errors = MeasurementValidator._validate_pollution(measurement)
            state_machine.add_errors(errors)
        elif measurement.type == "traffic":
            errors = MeasurementValidator._validate_traffic(measurement)
            state_machine.add_errors(errors)

    @staticmethod
    def _validate_pollution(m: RawMeasurement) -> list[str]:
        """Valide une mesure de pollution."""
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
        """Valide une mesure de trafic."""
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

    @staticmethod
    def _build_result(
        measurement: RawMeasurement, state_machine: MeasurementStateMachine
    ) -> ValidationResult:
        """Construit le résultat de validation."""
        current_state = state_machine.get_state()
        state_name = current_state.name()
        is_valid = current_state.is_valid()

        if is_valid:
            log.info(
                "✓ [%s] Measurement validated: %s from %s",
                state_name,
                measurement.type,
                measurement.city,
            )
        else:
            log.warning("✗ [%s] Validation failed: %s", state_name, state_machine.get_errors())

        return ValidationResult(
            state=state_name,
            valid=is_valid,
            measurement=measurement if is_valid else None,
            errors=state_machine.get_errors(),
            warnings=state_machine.get_warnings(),
        )