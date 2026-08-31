from datetime import datetime, timezone

from fastapi import FastAPI

from .models import ThresholdResponse

app = FastAPI(title="Referential Service")


_THRESHOLDS = [
    ThresholdResponse(
        id=1,
        key="NO2_WARNING",
        value=100.0,
        pollutant="no2",
        metric="pollution",
        unit="µg/m³",
        description="Warning threshold for NO2",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ),
    ThresholdResponse(
        id=2,
        key="NO2_CRITICAL",
        value=200.0,
        pollutant="no2",
        metric="pollution",
        unit="µg/m³",
        description="Critical threshold for NO2",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ),
    ThresholdResponse(
        id=3,
        key="TRAFFIC_Q_WARNING",
        value=500.0,
        metric="traffic",
        unit="veh/h",
        description="Warning threshold for traffic volume",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ),
    ThresholdResponse(
        id=4,
        key="TRAFFIC_Q_CRITICAL",
        value=800.0,
        metric="traffic",
        unit="veh/h",
        description="Critical threshold for traffic volume",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ),
]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/thresholds", response_model=list[ThresholdResponse])
def get_thresholds():
    return _THRESHOLDS
