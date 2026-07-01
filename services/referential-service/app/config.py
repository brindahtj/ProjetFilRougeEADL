from os import getenv

POSTGRES_HOST = getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = getenv("POSTGRES_USER", "urbanhub_user")
POSTGRES_PASSWORD = getenv("POSTGRES_PASSWORD", "urbanhub_password")
POSTGRES_DB = getenv("POSTGRES_DB", "urbanhub")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"