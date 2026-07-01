import logging
from datetime import datetime, timedelta
from typing import Optional, List, Any, Dict

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from Archive.Api_ingestion.alert_models import Alert, AlertCreate, AlertUpdate
from Archive.Api_ingestion.alert_store import AlertStore
from Archive.Api_ingestion.config import OUTPUT_DIR
from Archive.Api_ingestion.zone_utils import normalize_zone

log = logging.getLogger(__name__)

app = FastAPI(
    title="Smart City API",
    description="API de gestion des données IoT pour une ville intelligente",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Modèles Pydantic
# ─────────────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    timestamp: str


class PollutionDataPoint(BaseModel):
    city: str
    zone: str
    pollutant: str
    value: float
    unit: str
    latitude: float
    longitude: float
    timestamp: str


class TrafficDataPoint(BaseModel):
    city: str
    zone: str
    street: str
    section_id: str
    q: float
    etat_trafic: str
    latitude: float
    longitude: float
    timestamp: str


class StatisticsResponse(BaseModel):
    city: str
    pollutant: Optional[str] = None
    count: int
    mean: float
    min: float
    max: float
    last_update: str


class ApiError(BaseModel):
    code: str = Field(..., example="NOT_FOUND")
    message: str = Field(..., example="Ressource introuvable")
    details: Optional[Dict[str, Any]] = None


class ApiErrorEnvelope(BaseModel):
    error: ApiError


ALERT_RESPONSES = {
    400: {
        "model": ApiErrorEnvelope,
        "description": "Requête invalide",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Paramètre invalide",
                        "details": {"param": "level"},
                    }
                }
            }
        },
    },
    404: {
        "model": ApiErrorEnvelope,
        "description": "Ressource introuvable",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "ALERT_NOT_FOUND",
                        "message": "Alerte non trouvée",
                        "details": {"id": 99},
                    }
                }
            }
        },
    },
    409: {
        "model": ApiErrorEnvelope,
        "description": "Conflit métier",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "ALERT_CONFLICT",
                        "message": "Conflit lors de la mise à jour",
                    }
                }
            }
        },
    },
    422: {
        "model": ApiErrorEnvelope,
        "description": "Erreur de validation",
    },
    500: {
        "model": ApiErrorEnvelope,
        "description": "Erreur interne",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Erreur interne serveur",
                    }
                }
            }
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Aide erreur standardisée
# ─────────────────────────────────────────────────────────────────────────────

def api_error(status_code: int, code: str, message: str, details: dict | None = None):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Gestion validation
# ─────────────────────────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Requête invalide",
                "details": {"errors": exc.errors()},
            }
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints de santé
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    return {
        "status": "OK",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "name": "Smart City API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints Pollution
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/pollution/latest", response_model=List[PollutionDataPoint], tags=["Pollution"])
def get_latest_pollution(
    city: Optional[str] = Query(None, description="Filtrer par ville"),
    zone: Optional[str] = Query(None, description="Filtrer par zone (Paris Nord/Sud/Est/Ouest)"),
    pollutant: Optional[str] = Query(None, description="Filtrer par polluant (no2, pm25, etc.)"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre max de résultats"),
):
    try:
        pollution_file = OUTPUT_DIR / "pollution.csv"
        if not pollution_file.exists():
            raise HTTPException(status_code=404, detail="Aucune donnée pollution disponible")

        df = pd.read_csv(pollution_file)

        if city:
            df = df[df["city"].str.lower() == city.lower()]

        zone = normalize_zone(zone)
        if zone:
            if "zone" not in df.columns:
                raise HTTPException(status_code=400, detail="La colonne zone est absente des données.")
            df = df[df["zone"].str.lower() == zone.lower()]

        if pollutant:
            df = df[df["pollutant"].str.lower() == pollutant.lower()]

        df = df.sort_values("timestamp", ascending=False).head(limit)
        return [row.to_dict() for _, row in df.iterrows()]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lecture données : {str(e)}")


@app.get("/pollution/stats", response_model=List[StatisticsResponse], tags=["Pollution"])
def get_pollution_stats(
    city: Optional[str] = Query(None, description="Filtrer par ville"),
    zone: Optional[str] = Query(None, description="Filtrer par zone (Paris Nord/Sud/Est/Ouest)"),
    pollutant: Optional[str] = Query("no2", description="Polluant (défaut: no2)"),
    hours: int = Query(24, ge=1, le=720, description="Dernières N heures"),
):
    try:
        pollution_file = OUTPUT_DIR / "pollution.csv"
        if not pollution_file.exists():
            raise HTTPException(status_code=404, detail="Aucune donnée pollution disponible")

        df = pd.read_csv(pollution_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        df = df[df["timestamp"] >= cutoff_time]

        if city:
            df = df[df["city"].str.lower() == city.lower()]

        zone = normalize_zone(zone)
        if zone:
            if "zone" not in df.columns:
                raise HTTPException(status_code=400, detail="La colonne zone est absente des données.")
            df = df[df["zone"].str.lower() == zone.lower()]

        if pollutant:
            df = df[df["pollutant"].str.lower() == pollutant.lower()]

        stats = []
        for (c, p), group in df.groupby(["city", "pollutant"]):
            stats.append({
                "city": c,
                "pollutant": p,
                "count": len(group),
                "mean": float(group["value"].mean()),
                "min": float(group["value"].min()),
                "max": float(group["value"].max()),
                "last_update": group["timestamp"].max().isoformat(),
            })

        return stats

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur calcul statistiques : {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints Trafic
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/traffic/latest", response_model=List[TrafficDataPoint], tags=["Traffic"])
def get_latest_traffic(
    city: Optional[str] = Query("Paris", description="Ville (défaut: Paris)"),
    zone: Optional[str] = Query(None, description="Filtrer par zone (Paris Nord/Sud/Est/Ouest)"),
    street: Optional[str] = Query(None, description="Filtrer par rue"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre max de résultats"),
):
    try:
        traffic_file = OUTPUT_DIR / "traffic.csv"
        if not traffic_file.exists():
            raise HTTPException(status_code=404, detail="Aucune donnée trafic disponible")

        df = pd.read_csv(traffic_file)

        if city:
            df = df[df["city"].str.lower() == city.lower()]

        zone = normalize_zone(zone)
        if zone:
            if "zone" not in df.columns:
                raise HTTPException(status_code=400, detail="La colonne zone est absente des données.")
            df = df[df["zone"].str.lower() == zone.lower()]

        if street:
            df = df[df["street"].str.lower().str.contains(street.lower(), na=False)]

        df = df.sort_values("timestamp", ascending=False).head(limit)
        return [row.to_dict() for _, row in df.iterrows()]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lecture données : {str(e)}")


@app.get("/traffic/congestion", tags=["Traffic"])
def get_congestion_level(
    city: Optional[str] = Query("Paris", description="Ville"),
    zone: Optional[str] = Query(None, description="Filtrer par zone (Paris Nord/Sud/Est/Ouest)"),
):
    try:
        traffic_file = OUTPUT_DIR / "traffic.csv"
        if not traffic_file.exists():
            raise HTTPException(status_code=404, detail="Aucune donnée trafic")

        df = pd.read_csv(traffic_file)

        if city:
            df = df[df["city"].str.lower() == city.lower()]

        zone = normalize_zone(zone)
        if zone:
            if "zone" not in df.columns:
                raise HTTPException(status_code=400, detail="La colonne zone est absente des données.")
            df = df[df["zone"].str.lower() == zone.lower()]

        if df.empty:
            raise HTTPException(status_code=404, detail=f"Pas de données pour {city}")

        by_street = df.groupby("street")["q"].agg(["mean", "max", "count"]).reset_index()
        by_street.columns = ["street", "avg_q", "max_q", "measurements"]
        by_street["congestion"] = by_street["avg_q"].apply(
            lambda x: "🟢 Fluide" if x < 500 else "🟡 Modéré" if x < 800 else "🔴 Élevé"
        )

        return {
            "city": city,
            "timestamp": datetime.utcnow().isoformat(),
            "streets": by_street.to_dict("records"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur : {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints Corrélation
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/correlation/traffic-pollution", tags=["Correlation"])
def get_correlation(
    city: Optional[str] = Query("Paris", description="Ville"),
    zone: Optional[str] = Query(None, description="Filtrer par zone (Paris Nord/Sud/Est/Ouest)"),
    pollutant: Optional[str] = Query("no2", description="Polluant (défaut: no2)"),
):
    try:
        traffic_file = OUTPUT_DIR / "traffic.csv"
        pollution_file = OUTPUT_DIR / "pollution.csv"

        if not traffic_file.exists() or not pollution_file.exists():
            raise HTTPException(status_code=404, detail="Données manquantes")

        traffic_df = pd.read_csv(traffic_file)
        pollution_df = pd.read_csv(pollution_file)

        traffic_df = traffic_df[traffic_df["city"].str.lower() == city.lower()]
        pollution_df = pollution_df[
            (pollution_df["city"].str.lower() == city.lower()) &
            (pollution_df["pollutant"].str.lower() == pollutant.lower())
        ]

        zone = normalize_zone(zone)
        if zone:
            if "zone" not in traffic_df.columns or "zone" not in pollution_df.columns:
                raise HTTPException(status_code=400, detail="La colonne zone est absente des données.")
            traffic_df = traffic_df[traffic_df["zone"].str.lower() == zone.lower()]
            pollution_df = pollution_df[pollution_df["zone"].str.lower() == zone.lower()]

        if traffic_df.empty or pollution_df.empty:
            raise HTTPException(status_code=404, detail="Données insuffisantes")

        traffic_df["timestamp"] = pd.to_datetime(traffic_df["timestamp"])
        pollution_df["timestamp"] = pd.to_datetime(pollution_df["timestamp"])

        traffic_df["hour"] = traffic_df["timestamp"].dt.floor("H")
        pollution_df["hour"] = pollution_df["timestamp"].dt.floor("H")

        traffic_hourly = traffic_df.groupby("hour")["q"].mean()
        pollution_hourly = pollution_df.groupby("hour")["value"].mean()

        common_hours = traffic_hourly.index.intersection(pollution_hourly.index)
        if len(common_hours) < 2:
            raise HTTPException(status_code=400, detail="Pas assez de données communes")

        correlation = traffic_hourly[common_hours].corr(pollution_hourly[common_hours])

        return {
            "city": city,
            "pollutant": pollutant,
            "correlation": round(correlation, 3),
            "interpretation": (
                "Forte corrélation positive" if correlation > 0.7 else
                "Corrélation modérée" if correlation > 0.4 else
                "Corrélation faible" if correlation > 0 else
                "Corrélation négative"
            ),
            "data_points": len(common_hours),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur calcul corrélation : {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints Alerts
# ─────────────────────────────────────────────────────────────────────────────

alert_store = AlertStore()

@app.get(
    "/alerts",
    response_model=list[Alert],
    tags=["Alerts"],
    summary="Lister les alertes",
    description="Retourne la liste des alertes avec filtres optionnels.",
    responses=ALERT_RESPONSES,
)
def list_alerts(
    type: Optional[str] = Query(None, description="Filtre: pollution | traffic | correlation"),
    level: Optional[str] = Query(None, description="Filtre: WARNING | CRITICAL"),
    city: Optional[str] = Query(None, description="Filtre par ville"),
    zone: Optional[str] = Query(None, description="Filtre par zone"),
    active: Optional[bool] = Query(None, description="Filtre alertes actives/inactives"),
):
    try:
        items = alert_store.list()
        if type:
            items = [a for a in items if str(a.type).lower() == type.lower()]
        if level:
            items = [a for a in items if str(a.level).upper() == level.upper()]
        if city:
            items = [a for a in items if (a.city or "").lower() == city.lower()]
        if zone:
            items = [a for a in items if (a.zone or "").lower() == zone.lower()]
        if active is not None:
            items = [a for a in items if a.active == active]
        return items
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Impossible de lister les alertes",
                    "details": {"reason": str(exc)},
                }
            },
        )


@app.post(
    "/alerts",
    response_model=Alert,
    status_code=201,
    tags=["Alerts"],
    summary="Créer une alerte",
    description="Crée une alerte manuelle (ou injectée par un service).",
    responses=ALERT_RESPONSES,
)
def create_alert(alert: AlertCreate):
    try:
        created = alert_store.create(alert)
        return created
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Impossible de créer l'alerte",
                    "details": {"reason": str(exc)},
                }
            },
        )


@app.get(
    "/alerts/{alert_id}",
    response_model=Alert,
    tags=["Alerts"],
    summary="Récupérer une alerte",
    description="Retourne une alerte par son identifiant.",
    responses=ALERT_RESPONSES,
)
def get_alert(alert_id: int):
    try:
        alert = alert_store.get(alert_id)
        if not alert:
            return api_error(404, "ALERT_NOT_FOUND", "Alerte non trouvée", {"id": alert_id})
        return alert
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Impossible de récupérer l'alerte",
                    "details": {"reason": str(exc)},
                }
            },
        )


@app.put(
    "/alerts/{alert_id}",
    response_model=Alert,
    tags=["Alerts"],
    summary="Mettre à jour une alerte",
    description="Met à jour une alerte existante.",
    responses=ALERT_RESPONSES,
)
def update_alert(alert_id: int, alert: AlertUpdate):
    try:
        updated = alert_store.update(alert_id, alert)
        if not updated:
            return api_error(404, "ALERT_NOT_FOUND", "Alerte non trouvée", {"id": alert_id})
        return updated
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Impossible de mettre à jour l'alerte",
                    "details": {"reason": str(exc)},
                }
            },
        )


@app.delete(
    "/alerts/{alert_id}",
    status_code=204,
    tags=["Alerts"],
    summary="Supprimer une alerte",
    description="Supprime une alerte par son identifiant.",
    responses={
        **ALERT_RESPONSES,
        204: {"description": "Alerte supprimée"},
    },
)
def delete_alert(alert_id: int):
    try:
        deleted = alert_store.delete(alert_id)
        if not deleted:
            return api_error(404, "ALERT_NOT_FOUND", "Alerte non trouvée", {"id": alert_id})
        return JSONResponse(status_code=204, content=None)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Impossible de supprimer l'alerte",
                    "details": {"reason": str(exc)},
                }
            },
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)