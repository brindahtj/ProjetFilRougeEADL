# ─────────────────────────────────────────────────────────────────────────────
# Anomalies et seuils d'état
# ─────────────────────────────────────────────────────────────────────────────

MIN_ANOMALIES_WARNING = 1
MAX_ANOMALIES_WARNING = 2
MIN_ANOMALIES_CRITICAL = 3

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
ROUTING_KEY_ALERTS = "alerts"

# ─────────────────────────────────────────────────────────────────────────────
# Corrélation
# ─────────────────────────────────────────────────────────────────────────────

MIN_CORRELATION_PAIRS = 2
CORRELATION_PRECISION = 2

# ─────────────────────────────────────────────────────────────────────────────
# Seuils trafic Paris (comptage q)
# ─────────────────────────────────────────────────────────────────────────────

TRAFFIC_Q_FIXED_WARNING = 500  # seuil fixe alerte warning
TRAFFIC_Q_FIXED_CRITICAL = 800  # seuil fixe alerte critical

TRAFFIC_Q_PERCENTILE_WARNING = 0.80  # 80e percentile
TRAFFIC_Q_PERCENTILE_CRITICAL = 0.90  # 90e percentile

TRAFFIC_HISTORY_MIN_SIZE = 5  # minimum de mesures historiques pour calcul

# ─────────────────────────────────────────────────────────────────────────────
# Seuils pollution NO2 (µg/m3)
# ─────────────────────────────────────────────────────────────────────────────

NO2_WARNING = 100  # seuil alerte warning
NO2_CRITICAL = 200  # seuil alerte critical

# Détection "au-dessus de la moyenne"
TRAFFIC_ABOVE_MEAN_FACTOR = 1.20      # ex: 20% au-dessus de la moyenne déclenche alert
TRAFFIC_ABOVE_MEAN_STD_MULT = 1.5     # ou mean + 1.5 * std

POLLUTION_ABOVE_MEAN_FACTOR = 1.20    # idem pour NO2
POLLUTION_ABOVE_MEAN_STD_MULT = 1.5
HISTORY_MIN_FOR_STATS = 5             # minimum observations pour calculer mean/std