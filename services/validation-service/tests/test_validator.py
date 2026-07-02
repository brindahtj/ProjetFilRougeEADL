"""Tests unitaires pour le validateur."""
import pytest
from app.validator import MeasurementValidator
from app.models import RawMeasurement


class TestValidatorNormalState:
    """Tests pour l'état NORMAL."""

    def test_valid_pollution_measurement(self, valid_pollution_measurement):
        """Une mesure de pollution complète et valide → NORMAL."""
        result = MeasurementValidator.validate(valid_pollution_measurement)
        assert result.state == "NORMAL"
        assert result.valid is True
        assert len(result.errors) == 0

    def test_valid_traffic_measurement(self, valid_traffic_measurement):
        """Une mesure de trafic complète et valide → NORMAL."""
        result = MeasurementValidator.validate(valid_traffic_measurement)
        assert result.state == "NORMAL"
        assert result.valid is True
        assert len(result.errors) == 0

    def test_measurement_with_warnings_is_normal(self, valid_pollution_measurement):
        """Une mesure NORMAL avec avertissements (city hors whitelist) reste NORMAL."""
        valid_pollution_measurement.city = "london"  # Hors whitelist
        result = MeasurementValidator.validate(valid_pollution_measurement)
        assert result.state == "NORMAL"
        assert result.valid is True
        assert len(result.warnings) > 0


class TestValidatorCriticalState:
    """Tests pour l'état CRITICAL."""

    def test_incomplete_measurement(self, incomplete_measurement):
        """Une mesure incomplète (lat/lon manquantes) → CRITICAL."""
        result = MeasurementValidator.validate(incomplete_measurement)
        assert result.state == "CRITICAL"
        assert result.valid is False
        assert len(result.errors) >= 2  # lat et lon manquants

    def test_out_of_range_value(self, out_of_range_measurement):
        """Une mesure avec valeur hors limites → CRITICAL."""
        result = MeasurementValidator.validate(out_of_range_measurement)
        assert result.state == "CRITICAL"
        assert result.valid is False
        assert any("out of range" in e for e in result.errors)

    def test_invalid_type(self, invalid_type_measurement):
        """Un type invalide → CRITICAL."""
        result = MeasurementValidator.validate(invalid_type_measurement)
        assert result.state == "CRITICAL"
        assert result.valid is False

    def test_missing_city(self):
        """Mesure sans city → CRITICAL."""
        m = RawMeasurement(
            type="pollution",
            city="",
            pollutant="no2",
            value=85.5,
            latitude=48.8566,
            longitude=2.3522
        )
        result = MeasurementValidator.validate(m)
        assert result.state == "CRITICAL"
        assert result.valid is False

    def test_missing_pollutant(self):
        """Mesure pollution sans pollutant → CRITICAL."""
        m = RawMeasurement(
            type="pollution",
            city="paris",
            pollutant=None,
            value=85.5,
            latitude=48.8566,
            longitude=2.3522
        )
        result = MeasurementValidator.validate(m)
        assert result.state == "CRITICAL"


class TestValidatorPollutionSpecific:
    """Tests spécifiques à la pollution."""

    def test_allowed_pollutants(self):
        """Tous les polluants autorisés sont acceptés."""
        allowed = {"no2", "pm25", "pm10", "o3", "co"}
        for pollutant in allowed:
            m = RawMeasurement(
                type="pollution",
                city="paris",
                pollutant=pollutant,
                value=50.0,
                latitude=48.8566,
                longitude=2.3522
            )
            result = MeasurementValidator.validate(m)
            assert result.state == "NORMAL"

    def test_disallowed_pollutant(self):
        """Un polluant non autorisé → CRITICAL."""
        m = RawMeasurement(
            type="pollution",
            city="paris",
            pollutant="unknown_gas",
            value=50.0,
            latitude=48.8566,
            longitude=2.3522
        )
        result = MeasurementValidator.validate(m)
        assert result.state == "CRITICAL"


class TestValidatorTrafficSpecific:
    """Tests spécifiques au trafic."""

    def test_missing_street(self):
        """Mesure trafic sans street → CRITICAL."""
        m = RawMeasurement(
            type="traffic",
            city="paris",
            street=None,
            section_id="sec_001",
            q=250.0,
            latitude=48.8566,
            longitude=2.3522
        )
        result = MeasurementValidator.validate(m)
        assert result.state == "CRITICAL"

    def test_missing_section_id(self):
        """Mesure trafic sans section_id → CRITICAL."""
        m = RawMeasurement(
            type="traffic",
            city="paris",
            street="Rue de la Paix",
            section_id=None,
            q=250.0,
            latitude=48.8566,
            longitude=2.3522
        )
        result = MeasurementValidator.validate(m)
        assert result.state == "CRITICAL"

    def test_traffic_q_out_of_range(self):
        """Q hors limites → CRITICAL."""
        m = RawMeasurement(
            type="traffic",
            city="paris",
            street="Rue de la Paix",
            section_id="sec_001",
            q=15000.0,  # > MAX
            latitude=48.8566,
            longitude=2.3522
        )
        result = MeasurementValidator.validate(m)
        assert result.state == "CRITICAL"


class TestValidatorCoordinates:
    """Tests des coordonnées géographiques."""

    def test_valid_coordinates(self):
        """Coordonnées valides sont acceptées."""
        m = RawMeasurement(
            type="pollution",
            city="paris",
            pollutant="no2",
            value=85.5,
            latitude=0.0,
            longitude=0.0
        )
        result = MeasurementValidator.validate(m)
        assert result.state == "NORMAL"

    def test_latitude_out_of_range(self):
        """Latitude invalide → CRITICAL."""
        m = RawMeasurement(
            type="pollution",
            city="paris",
            pollutant="no2",
            value=85.5,
            latitude=100.0,  # > 90
            longitude=2.3522
        )
        result = MeasurementValidator.validate(m)
        assert result.state == "CRITICAL"

    def test_longitude_out_of_range(self):
        """Longitude invalide → CRITICAL."""
        m = RawMeasurement(
            type="pollution",
            city="paris",
            pollutant="no2",
            value=85.5,
            latitude=48.8566,
            longitude=200.0  # > 180
        )
        result = MeasurementValidator.validate(m)
        assert result.state == "CRITICAL"