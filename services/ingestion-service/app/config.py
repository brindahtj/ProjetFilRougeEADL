from os import getenv

RABBITMQ_USER = getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = getenv("RABBITMQ_PASS", "guest")
RABBITMQ_HOST = getenv("RABBITMQ_HOST", 'rabbitmq')
RABBITMQ_PORT = int(getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_QUEUE= getenv("RABBITMQ_QUEUE", "sensors_data")
EXCHANGE = getenv("RABBITMQ_EXCHANGE", "logs")
RATE           = int(getenv("MEASUREMENTS_PER_SECOND", "10"))
VALIDATION_SERVICE_URL = getenv(
    "VALIDATION_SERVICE_URL", "http://validation:8002"
)
