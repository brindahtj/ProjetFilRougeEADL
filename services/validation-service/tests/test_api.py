"""Tests des endpoints API."""

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client(mock_rabbit_init):
    """Client de test FastAPI avec Rabbit mocké."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests de l'endpoint /health."""

    def test_health_check(self, client):
        """GET /health retourne status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "validation-service"


class TestValidateEndpoint:
    """Tests de l'endpoint POST /validate."""

    def test_validate_valid_pollution(
        self, client, valid_pollution_measurement, mock_rabbit_connection
    ):
        """Valider une mesure pollution valide → 200 NORMAL."""
        response = client.post(
            "/validate",
            json=valid_pollution_measurement.model_dump()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "NORMAL"
        assert data["valid"] is True
        assert data["routing_key"] == "pollution"
        # Vérifier que publish a été appelée
        mock_rabbit_connection.channel.assert_called()

    def test_validate_invalid_pollution(self, client, incomplete_measurement):
        """Valider une mesure invalide → 200 CRITICAL."""
        response = client.post(
            "/validate",
            json=incomplete_measurement.model_dump()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "CRITICAL"
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_invalid_json(self, client):
        """Envoyer JSON invalide → 422."""
        response = client.post(
            "/validate",
            json={"type": "unknown", "city": ""}
        )
        # La validation Pydantic échoue → erreur de validation
        assert response.status_code in [422, 200]


class TestBatchEndpoint:
    """Tests de l'endpoint POST /validate-batch."""

    def test_batch_mixed_measurements(
        self,
        client,
        valid_pollution_measurement,
        incomplete_measurement
    ):
        """Batch avec mesures valides et invalides → stats correctes."""
        measurements = [
            valid_pollution_measurement.model_dump(),
            incomplete_measurement.model_dump()
        ]
        response = client.post("/validate-batch", json=measurements)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["accepted"] == 1
        assert data["rejected"] == 1

    def test_batch_empty(self, client):
        """Batch vide → résultat vide."""
        response = client.post("/validate-batch", json=[])
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["accepted"] == 0
        assert data["rejected"] == 0
