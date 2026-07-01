from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class CorrelationORM(Base):
    __tablename__ = "correlations"

    id = Column(Integer, primary_key=True)
    city = Column(String(100), nullable=False)
    zone = Column(String(100))
    pollution_avg = Column(Float)
    traffic_avg = Column(Float)
    correlation_value = Column(Float)
    sample_size = Column(Integer)
    time_window = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

class CorrelationResponse(BaseModel):
    id: int
    city: str
    zone: Optional[str]
    pollution_avg: float
    traffic_avg: float
    correlation_value: Optional[float] = None
    sample_size: Optional[int] = None
    time_window: str
    created_at: datetime

    class Config:
        from_attributes = True