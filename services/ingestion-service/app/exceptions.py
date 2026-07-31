class InvalidSensorIdError(Exception):
    """Levée uniquement si le sensor_id est absent ou malformé dans l'URL."""
    pass

class MetricValidationError(Exception):
    """Levée si le body JSON n'est pas lisible."""
    pass