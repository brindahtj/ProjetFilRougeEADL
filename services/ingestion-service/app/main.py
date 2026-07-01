import logging
import requests
from fastapi import FastAPI, HTTPException
from typing import List
from .models import RawMeasurement
from .config import VALIDATION_SERVICE_URL

log = logging.getLogger("ingestion")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Ingestion Service")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/measurements", status_code=202)
def ingest(measurements: List[RawMeasurement]):
    """Reçoit les mesures brutes et les envoie à validation-service."""
    try:
        results = []
        for m in measurements:
            # Envoyer à validation-service
            resp = requests.post(
                f"{VALIDATION_SERVICE_URL}/validate",
                json=m.dict()
            )
            result = resp.json()
            results.append(result)

            if result.get("valid"):
                log.info("✓ Measurement accepted: %s from %s", m.type, m.city)
            else:
                log.warning("✗ Measurement rejected: %s", result.get("errors"))

        return {"accepted": len([r for r in results if r.get("valid")]), "results": results}
    except Exception as exc:
        log.exception("Ingest error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))