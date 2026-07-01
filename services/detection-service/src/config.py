from os import getenv

# Rabbit
RABBIT_HOST = getenv("RABBIT_HOST", "rabbitmq")
RABBIT_PORT = int(getenv("RABBIT_PORT", "5672"))
RABBIT_USER = getenv("RABBIT_USER", "guest")
RABBIT_PASS = getenv("RABBIT_PASS", "guest")
EXCHANGE = getenv("EXCHANGE", "urbanhub")

# Referentiel (service qui expose /thresholds)
REFERENTIAL_URL = getenv("REFERENTIAL_URL", "http://referential:8001")

# Defaults (fallback si referential indisponible)
DEFAULTS = {
    "NO2_WARNING": 100.0,
    "NO2_CRITICAL": 200.0,
    "TRAFFIC_Q_WARNING": 500.0,
    "TRAFFIC_Q_CRITICAL": 800.0
}

# Refresh interval (sec) for thresholds
THRESHOLD_REFRESH_SECONDS = int(getenv("THRESHOLD_REFRESH_SECONDS", "300"))

# Buffer / policy
POLL_PREFETCH = int(getenv("POLL_PREFETCH", "5"))