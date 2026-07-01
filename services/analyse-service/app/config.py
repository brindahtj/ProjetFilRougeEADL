from os import getenv

RABBIT_HOST = getenv("RABBIT_HOST", "rabbitmq")
RABBIT_USER = getenv("RABBIT_USER", "guest")
RABBIT_PASS = getenv("RABBIT_PASS", "guest")
EXCHANGE = getenv("EXCHANGE", "urbanhub")

POSTGRES_HOST = getenv("POSTGRES_HOST", "postgres")
POSTGRES_USER = getenv("POSTGRES_USER", "urbanhub_user")
POSTGRES_PASSWORD = getenv("POSTGRES_PASSWORD", "urbanhub_password")
POSTGRES_DB = getenv("POSTGRES_DB", "urbanhub")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"