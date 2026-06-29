class SmartCityException(Exception):
    """Exception de base pour tout le projet."""

    def __init__(self, message: str, context: str = None):
        self.message = message
        self.context = context
        super().__init__(self.message)

    def __str__(self):
        if self.context:
            return f"[{self.context}] {self.message}"
        return self.message


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions Api_ingestion
# ─────────────────────────────────────────────────────────────────────────────


class SensorError(SmartCityException):
    """Erreur liée au capteur ou son état."""
    pass


class ApiClientError(SmartCityException):
    """Erreur liée à un client API (OpenAQ, HERE, etc.)."""
    pass


class RepositoryError(SmartCityException):
    """Erreur liée à la persistance (CSV, DB, etc.)."""
    pass


class PublisherError(SmartCityException):
    """Erreur liée à la publication des messages (RabbitMQ, etc.)."""
    pass


class DataValidationError(SmartCityException):
    """Erreur de validation de données."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions MoteurCorrelation
# ─────────────────────────────────────────────────────────────────────────────


class CorrelationError(SmartCityException):
    """Erreur liée au calcul de corrélation."""
    pass


class ConsumerError(SmartCityException):
    """Erreur liée à la consommation de messages (RabbitMQ)."""
    pass


class BufferError(SmartCityException):
    """Erreur liée à la bufferisation de messages."""
    pass