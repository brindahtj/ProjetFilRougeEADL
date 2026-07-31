from os import getenv

RABBITMQ_USER = getenv("RABBIT_USER", "guest")
RABBIT_PASS = getenv("RABBIT_PASS", "guest")
RABBIT_HOST = getenv("RABBIT_HOST")
RABBIT_PORT = int(getenv("RABBIT_PORT", "5672"))
EXCHANGE = getenv("RABBIT_EXCHANGE", "logs")
TARGET_API_URL = getenv("TARGET_API_URL", "http://api-python:8000")
RATE           = int(getenv("MEASUREMENTS_PER_SECOND", "10"))
VALIDATION_SERVICE_URL = getenv(
    "VALIDATION_SERVICE_URL", "http://validation-service:8000"
)
