from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from statistics import mean
from .models import Base, CorrelationORM
from .config import DATABASE_URL
import math

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base.metadata.create_all(engine)

def pearson_correlation(x: list[float], y: list[float]) -> float | None:
    """Calcule la corrélation de Pearson."""
    if not x or not y or len(x) != len(y):
        return None
    n = len(x)
    mean_x = mean(x)
    mean_y = mean(y)
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
    den_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
    denom = den_x * den_y
    if denom == 0:
        return None
    return num / denom

def save_correlation(city: str, zone: str, pollution_avg: float, traffic_avg: float, time_window: str):
    """Sauvegarde une corrélation en DB et retourne l'objet."""
    db = SessionLocal()
    try:
        # Calculer corrélation (nécessite historique, simplifié ici)
        corr = pearson_correlation([pollution_avg], [traffic_avg])  # Simple placeholder

        correlation = CorrelationORM(
            city=city,
            zone=zone,
            pollution_avg=pollution_avg,
            traffic_avg=traffic_avg,
            correlation_value=corr,
            sample_size=1,
            time_window=time_window
        )
        db.add(correlation)
        db.commit()
        db.refresh(correlation)
        return correlation
    finally:
        db.close()

def get_correlations(city: str = None, zone: str = None, limit: int = 100):
    """Récupère les corrélations."""
    db = SessionLocal()
    try:
        query = db.query(CorrelationORM)
        if city:
            query = query.filter(CorrelationORM.city == city)
        if zone:
            query = query.filter(CorrelationORM.zone == zone)
        return query.order_by(CorrelationORM.created_at.desc()).limit(limit).all()
    finally:
        db.close()