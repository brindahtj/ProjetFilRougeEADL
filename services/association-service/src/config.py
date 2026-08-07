from os import getenv

RABBITMQ_USER = getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = getenv("RABBITMQ_PASS", "guest")
RABBITMQ_HOST = getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(getenv("RABBITMQ_PORT", "5672"))
EXCHANGE = getenv("RABBITMQ_EXCHANGE", "logs")
TARGET_API_URL = getenv("TARGET_API_URL", "http://api-python:8000")
RATE           = int(getenv("MEASUREMENTS_PER_SECOND", "10"))

# Buffer size before triggering association
BUFFER_SIZE = int(getenv("BUFFER_SIZE", "10"))

# Time window (minutes) to associate measurements from same zone
TIME_WINDOW_MINUTES = int(getenv("TIME_WINDOW_MINUTES", "5"))
