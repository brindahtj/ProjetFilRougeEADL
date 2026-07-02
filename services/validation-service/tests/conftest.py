import pytest
from unittest.mock import Mock, patch, MagicMock
from app.models import RawMeasurement


@pytest.fixture
def valid_pollution_measurement():
    """Fixture : mesure de pollution valide."""
    return RawMeasurement(
        type="pollution",
        city="paris",
        zone="nord",
        pollutant="no2",
        value=85.5,
        latitude=48.8566,
        longitude=2.3522,
        timestamp=None
    )


@pytest.fixture
def valid_traffic_measurement():
    """Fixture : mesure de trafic valide."""
    return RawMeasurement(
        type="traffic",
        city="lyon",
        zone="centre",
        street="Rue de la Paix",
        section_id="sec_001",
        q=250.0,
        latitude=45.7640,
        longitude=4.8357,
        timestamp=None
    )


@pytest.fixture
def incomplete_measurement():
    """Fixture : mesure incomplète (manque latitude et longitude)."""
    return RawMeasurement(
        type="pollution",
        city="paris",
        pollutant="no2",
        value=85.5,
        latitude=None,
        longitude=None
    )


@pytest.fixture
def out_of_range_measurement():
    """Fixture : mesure aberrante (valeur hors limites)."""
    return RawMeasurement(
        type="pollution",
        city="paris",
        pollutant="no2",
        value=5000.0,  # > MAX_VALUE
        latitude=48.8566,
        longitude=2.3522
    )


@pytest.fixture
def invalid_type_measurement():
    """Fixture : type invalide."""
    return RawMeasurement(
        type="unknown",
        city="paris",
        latitude=48.8566,
        longitude=2.3522
    )


@pytest.fixture
def mock_rabbit_connection():
    """Mock de la connexion RabbitMQ."""
    with patch("app.main.publisher_connection") as mock_conn:
        mock_channel = MagicMock()
        mock_conn.channel.return_value = mock_channel
        yield mock_conn


@pytest.fixture
def mock_rabbit_init():
    """Mock de l'initialisation RabbitMQ."""
    with patch("app.main.init_rabbit"):
        yield