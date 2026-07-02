from os import getenv

RABBIT_HOST = getenv("RABBIT_HOST", "rabbitmq")
RABBIT_PORT = int(getenv("RABBIT_PORT", "5672"))
RABBIT_USER = getenv("RABBIT_USER", "guest")
RABBIT_PASS = getenv("RABBIT_PASS", "guest")
EXCHANGE = getenv("EXCHANGE", "urbanhub")

# Thresholds for validation
LATITUDE_MIN, LATITUDE_MAX = -90, 90
LONGITUDE_MIN, LONGITUDE_MAX = -180, 180

POLLUTION_ALLOWED = {"no2", "pm25", "pm10", "o3", "co"}
POLLUTION_VALUE_MIN = 0
POLLUTION_VALUE_MAX = 1000  # µg/m³

TRAFFIC_Q_MIN = 0
TRAFFIC_Q_MAX = 10000  # veh/h

CITIES_ALLOWED = {"paris"}
ZONES_ALLOWED = {"nord", "sud", "est", "ouest", "centre"}

# API Documentation
API_TITLE = "Validation Service"
API_DESCRIPTION = """
Service de validation des mesures brutes (pollution et trafic).

## États des mesures
- **NORMAL** : donnée complète et conforme → publication
- **CRITICAL** : donnée incomplète ou aberrante → mise de côté

## Flux
1. Ingestion Service envoie mesure brute
2. Validation Service valide la mesure
3. Si NORMAL → publiée sur RabbitMQ
4. Si CRITICAL → rejetée
"""
API_VERSION = "1.0.0"
