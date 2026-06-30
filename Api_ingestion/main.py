import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd

from Api_ingestion.config import OUTPUT_DIR
from Api_ingestion.zone_utils import normalize_zone

log = logging.getLogger(__name__)

app = FastAPI(
    title="Smart City API",
    description="API de gestion des données IoT pour une ville intelligente",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Autoriser CORS pour front-end
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Modèles de réponse (Pydantic)
# ─────────────────────────────────────────────────────────────────────────────


from pydantic import BaseModel


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


class AlertMessage(BaseModel):
    type: str
    level: str
    city: Optional[str] = None
    value: Optional[float] = None
    timestamp: str


class StatisticsResponse(BaseModel):
    city: str
    pollutant: Optional[str] = None
    count: int
    mean: float
    min: float
    max: float
    last_update: str


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints de santé
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Vérifier la santé de l'API."""
    return {
        "status": "OK",
        "timestamp": datetime.utcnow().isoformat(),
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
    """
    Récupère les dernières mesures de pollution.

    **Paramètres:**
    - `city`: Filtrer par ville (ex: Paris, Lyon)
    - `pollutant`: Filtrer par polluant (ex: no2, pm25, pm10, o3, co)
    - `limit`: Nombre max de résultats (défaut: 100)

    **Exemple:** `/pollution/latest?city=Paris&pollutant=no2&limit=50`
    """
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lecture données : {str(e)}")


@app.get("/pollution/stats", response_model=List[StatisticsResponse], tags=["Pollution"])
def get_pollution_stats(
    city: Optional[str] = Query(None, description="Filtrer par ville"),
    zone: Optional[str] = Query(None, description="Filtrer par zone (Paris Nord/Sud/Est/Ouest)"),
    pollutant: Optional[str] = Query("no2", description="Polluant (défaut: no2)"),
    hours: int = Query(24, ge=1, le=720, description="Dernières N heures"),
):
    """
    Récupère les statistiques de pollution (moyenne, min, max).

    **Paramètres:**
    - `city`: Ville à analyser
    - `pollutant`: Polluant à analyser (défaut: no2)
    - `hours`: Fenêtre temporelle en heures (défaut: 24)

    **Exemple:** `/pollution/stats?city=Paris&pollutant=no2&hours=24`
    """
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
    """
    Récupère les dernières mesures de trafic.

    **Paramètres:**
    - `city`: Ville (défaut: Paris)
    - `street`: Filtrer par rue
    - `limit`: Nombre max de résultats

    **Exemple:** `/traffic/latest?city=Paris&street=Vaugirard&limit=50`
    """
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lecture données : {str(e)}")


@app.get("/traffic/congestion", tags=["Traffic"])
def get_congestion_level(
    city: Optional[str] = Query("Paris", description="Ville"),
    zone: Optional[str] = Query(None, description="Filtrer par zone (Paris Nord/Sud/Est/Ouest)"),
):
    """
    Niveau de congestion moyen par ville.

    **Exemple:** `/traffic/congestion?city=Paris`
    """
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

        # Moyenne par rue
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
    """
    Corrélation entre trafic et pollution par ville.

    **Exemple:** `/correlation/traffic-pollution?city=Paris&pollutant=no2`
    """
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

        # Agréger par heure
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur calcul corrélation : {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Root
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/", tags=["Root"])
def root():
    """Bienvenue sur l'API Smart City."""
    return {
        "name": "Smart City API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)