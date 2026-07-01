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

CITIES_ALLOWED = {"paris", "lyon", "marseille"}
ZONES_ALLOWED = {"nord", "sud", "est", "ouest", "centre"}