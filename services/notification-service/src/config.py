from os import getenv

RABBITMQ_HOST = getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = getenv("RABBITMQ_PASS", "guest")
EXCHANGE = getenv("RABBITMQ_EXCHANGE", "logs")
