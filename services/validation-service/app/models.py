from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime


class RawMeasurement(BaseModel):
    """Modèle de mesure brute reçue par l'API."""
    type: Literal["pollution", "traffic"] = Field(
        ..., description="Type de mesure: pollution ou traffic"
    )
    city: str = Field(..., description="Ville concernée")
    zone: Optional[str] = Field(None, description="Zone de la ville")
    pollutant: Optional[str] = Field(None, description="Polluant (pollution)")
    value: Optional[float] = Field(None, description="Valeur mesurée")
    street: Optional[str] = Field(None, description="Rue (trafic)")
    section_id: Optional[str] = Field(None, description="Section ID (trafic)")
    q: Optional[float] = Field(None, description="Trafic métrique Q (véhicules/h)")
    latitude: Optional[float] = Field(None, description="Latitude (-90 à 90)")
    longitude: Optional[float] = Field(None, description="Longitude (-180 à 180)")
    timestamp: Optional[datetime] = Field(None, description="Timestamp de la mesure")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "pollution",
                "city": "paris",
                "zone": "nord",
                "pollutant": "no2",
                "value": 85.5,
                "latitude": 48.8566,
                "longitude": 2.3522,
                "timestamp": "2026-07-02T10:30:00Z"
            }
        }


class ValidationResult(BaseModel):
    """Résultat de validation d'une mesure."""
    state: Literal["NORMAL", "CRITICAL"] = Field(
        ..., description="État de la mesure: NORMAL (valide) ou CRITICAL (invalide)"
    )
    valid: bool = Field(
        ..., description="Indicateur de validité cohérent avec state"
    )
    measurement: Optional[RawMeasurement] = Field(
        None, description="Mesure validée (si valide)"
    )
    errors: list[str] = Field(
        default_factory=list, description="Erreurs (données incomplètes/aberrantes)"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Avertissements (non bloquants)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "state": "NORMAL",
                "valid": True,
                "measurement": {
                    "type": "pollution",
                    "city": "paris",
                    "pollutant": "no2",
                    "value": 85.5,
                    "latitude": 48.8566,
                    "longitude": 2.3522
                },
                "errors": [],
                "warnings": []
            }
        }


class ValidationResponse(BaseModel):
    """Réponse API pour une validation simple."""
    state: Literal["NORMAL", "CRITICAL"]
    valid: bool
    message: str
    routing_key: Optional[str] = None
    errors: list[str] = []
    warnings: list[str] = []


class BatchValidationResponse(BaseModel):
    """Réponse API pour une validation par lot."""
    results: list[ValidationResponse]
    total: int = Field(..., description="Nombre total de mesures traitées")
    accepted: int = Field(..., description="Nombre de mesures acceptées (NORMAL)")
    rejected: int = Field(..., description="Nombre de mesures rejetées (CRITICAL)")


class HealthResponse(BaseModel):
    """Réponse du health check."""
    status: str
    service: str = "validation-service"
    version: str = "1.0.0"