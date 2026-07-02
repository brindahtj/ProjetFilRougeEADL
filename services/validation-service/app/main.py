import logging
import pika
import json
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from .models import (
    RawMeasurement,
    ValidationResponse,
    BatchValidationResponse,
    HealthResponse,
)
from .validator import MeasurementValidator
from .config import RABBIT_HOST, RABBIT_USER, RABBIT_PASS, EXCHANGE
from .config import API_TITLE, API_DESCRIPTION, API_VERSION

log = logging.getLogger("validation")
logging.basicConfig(level=logging.INFO)

# RabbitMQ connection
publisher_connection = None


def init_rabbit():
    """Initialise la connexion RabbitMQ."""
    global publisher_connection
    try:
        creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
        params = pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds, heartbeat=600)
        publisher_connection = pika.BlockingConnection(params)
        ch = publisher_connection.channel()
        ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
        log.info("✓ RabbitMQ initialized")
    except Exception as e:
        log.error("✗ RabbitMQ initialization failed: %s", e)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_rabbit()
    yield
    # Shutdown
    if publisher_connection:
        publisher_connection.close()
        log.info("RabbitMQ connection closed")


# Configuration Swagger/OpenAPI
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    contact={"name": "Smart City Team", "email": "team@smartcity.local"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES DE SANTÉ
# ─────────────────────────────────────────────────────────────────────────────


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Vérifier la santé du service",
    description="Endpoint de santé pour les health checks",
)
def health():
    """Retourne le statut du service."""
    return HealthResponse(status="ok")


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES DE VALIDATION
# ─────────────────────────────────────────────────────────────────────────────


@app.post(
    "/validate",
    response_model=ValidationResponse,
    tags=["Validation"],
    summary="Valider une mesure unique",
    description="""
    Valide une mesure brute (pollution ou trafic).
    
    ### États possibles
    - **NORMAL** : donnée complète et conforme → publication sur RabbitMQ
    - **CRITICAL** : donnée incomplète ou aberrante → rejet et mise de côté
    
    ### Validations effectuées
    - Type de mesure (pollution ou traffic)
    - Champs obligatoires (city, latitude, longitude, timestamp)
    - Plages de valeurs (latitude, longitude, valeur, q)
    - Cohérence du timestamp (pas plus de 5 min dans le futur, pas plus de 24h dans le passé)
    - Contraintes spécifiques au type (pollutant, value pour pollution ; street, section_id, q pour traffic)
    """,
    responses={
        200: {
            "description": "Validation réussie",
            "content": {
                "application/json": {
                    "example": {
                        "state": "NORMAL",
                        "valid": True,
                        "message": "Measurement published to event bus",
                        "routing_key": "pollution",
                        "errors": [],
                        "warnings": [],
                    }
                }
            },
        },
        400: {
            "description": "Erreur de validation",
            "content": {
                "application/json": {
                    "example": {
                        "state": "CRITICAL",
                        "valid": False,
                        "message": "Measurement rejected",
                        "errors": ["city is required"],
                        "warnings": [],
                    }
                }
            },
        },
    },
)
def validate(measurement: RawMeasurement):
    """Valide une mesure et la publie si NORMAL."""
    try:
        result = MeasurementValidator.validate(measurement)

        if result.state == "NORMAL" and result.measurement:
            _publish_measurement(result.measurement)
            return ValidationResponse(
                state=result.state,
                valid=True,
                message="Measurement published to event bus",
                routing_key=result.measurement.type,
                errors=result.errors,
                warnings=result.warnings,
            )
        else:
            return ValidationResponse(
                state=result.state,
                valid=False,
                message="Measurement rejected (incomplete or anomalous data)",
                errors=result.errors,
                warnings=result.warnings,
            )
    except Exception as e:
        log.exception("Validation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/validate-batch",
    response_model=BatchValidationResponse,
    tags=["Validation"],
    summary="Valider un lot de mesures",
    description="""
    Valide un lot de mesures en une seule requête.
    
    Retourne le nombre total, acceptées (NORMAL) et rejetées (CRITICAL).
    """,
    responses={
        200: {
            "description": "Batch traité",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "state": "NORMAL",
                                "valid": True,
                                "message": "Measurement published to event bus",
                                "routing_key": "pollution",
                            }
                        ],
                        "total": 1,
                        "accepted": 1,
                        "rejected": 0,
                    }
                }
            },
        }
    },
)
def validate_batch(measurements: list[RawMeasurement]):
    """Valide un lot de mesures."""
    try:
        results = []
        accepted_count = 0
        rejected_count = 0

        for m in measurements:
            result = MeasurementValidator.validate(m)

            response = ValidationResponse(
                state=result.state,
                valid=result.valid,
                message=(
                    "Measurement published to event bus"
                    if result.state == "NORMAL"
                    else "Measurement rejected (incomplete or anomalous data)"
                ),
                routing_key=result.measurement.type if result.measurement else None,
                errors=result.errors,
                warnings=result.warnings,
            )

            if result.state == "NORMAL" and result.measurement:
                _publish_measurement(result.measurement)
                accepted_count += 1
                log.info(
                    "✓ [NORMAL] Published: %s from %s",
                    result.measurement.type,
                    result.measurement.city,
                )
            else:
                rejected_count += 1
                log.warning("✗ [CRITICAL] Not published: %s", result.errors)

            results.append(response)

        return BatchValidationResponse(
            results=results,
            total=len(measurements),
            accepted=accepted_count,
            rejected=rejected_count,
        )
    except Exception as e:
        log.exception("Batch validation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# FONCTIONS UTILITAIRES
# ─────────────────────────────────────────────────────────────────────────────


def _publish_measurement(measurement: RawMeasurement) -> None:
    """Publie une mesure sur RabbitMQ."""
    try:
        ch = publisher_connection.channel()
        routing_key = measurement.type
        body = json.dumps(measurement.dict(), default=str)
        ch.basic_publish(exchange=EXCHANGE, routing_key=routing_key, body=body)
        log.info("✓ Published to %s: %s", routing_key, measurement.city)
    except Exception as e:
        log.exception("Failed to publish measurement: %s", e)
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
