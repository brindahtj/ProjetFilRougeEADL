# ─────────────────────────────────────────────────────────────────────────────
# Anomalies et seuils d'état
# ─────────────────────────────────────────────────────────────────────────────

# Thresholds pour les transitions d'état du capteur
MIN_ANOMALIES_WARNING = 1  # Passer en WARNING si >= 1
MAX_ANOMALIES_WARNING = 2  # Rester en WARNING si <= 2
MIN_ANOMALIES_CRITICAL = 3  # Passer en CRITICAL si >= 3

# ─────────────────────────────────────────────────────────────────────────────
# Polluants autorisés
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED_POLLUTANTS = {"no2", "pm25", "pm10", "o3", "co"}

# ─────────────────────────────────────────────────────────────────────────────
# Noms des états
# ─────────────────────────────────────────────────────────────────────────────

STATE_NORMAL = "NORMAL"
STATE_WARNING = "WARNING"
STATE_CRITICAL = "CRITICAL"

# ─────────────────────────────────────────────────────────────────────────────
# Routing keys RabbitMQ
# ─────────────────────────────────────────────────────────────────────────────

ROUTING_KEY_POLLUTION = "pollution"
ROUTING_KEY_TRAFFIC = "traffic"
ROUTING_KEY_CORRELATION = "correlation"

# ─────────────────────────────────────────────────────────────────────────────
# Corrélation
# ─────────────────────────────────────────────────────────────────────────────

MIN_CORRELATION_PAIRS = 2  # Minimum de paires pour calculer une corrélation
CORRELATION_PRECISION = 2  # Arrondir à 2 décimales