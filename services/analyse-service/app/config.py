from os import getenv

RABBIT_USER = getenv("RABBIT_USER", "guest")
RABBIT_PASS = getenv("RABBIT_PASS", "guest")
RABBIT_HOST = getenv("RABBIT_HOST")
RABBIT_PORT = int(getenv("RABBIT_PORT", "5672"))
EXCHANGE = getenv("RABBIT_EXCHANGE", "logs")
TARGET_API_URL = getenv("TARGET_API_URL", "http://api-python:8000")
RATE           = int(getenv("MEASUREMENTS_PER_SECOND", "10"))
POSTGRES_HOST = getenv("POSTGRES_HOST", "postgres")
POSTGRES_USER = getenv("POSTGRES_USER", "urbanhub_user")
POSTGRES_PASSWORD = getenv("POSTGRES_PASSWORD", "urbanhub_password")
POSTGRES_DB = getenv("POSTGRES_DB", "urbanhub")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"
