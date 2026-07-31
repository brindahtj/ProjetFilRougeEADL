from os import getenv

RABBITMQ_USER = getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = getenv("RABBITMQ_PASS", "guest")
RABBITMQ_HOST = getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(getenv("RABBITMQ_PORT", "5672"))
EXCHANGE = getenv("RABBITMQ_EXCHANGE", "logs")
TARGET_API_URL = getenv("TARGET_API_URL", "http://api-python:8000")
RATE           = int(getenv("MEASUREMENTS_PER_SECOND", "10"))
POSTGRES_HOST = getenv("POSTGRES_HOST", "postgres")
POSTGRES_USER = getenv("POSTGRES_USER", "urbanhub_user")
POSTGRES_PASSWORD = getenv("POSTGRES_PASSWORD", "urbanhub_password")
POSTGRES_DB = getenv("POSTGRES_DB", "urbanhub")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"
