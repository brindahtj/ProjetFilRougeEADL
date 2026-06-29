class SmartCityException(Exception):
    """Exception de base pour tout le projet."""


class SensorError(SmartCityException):
    """Erreur liée au capteur."""


class ApiClientError(SmartCityException):
    """Erreur liée à un client API."""


class RepositoryError(SmartCityException):
    """Erreur liée à la persistance."""


class PublisherError(SmartCityException):
    """Erreur liée à la publication des messages."""