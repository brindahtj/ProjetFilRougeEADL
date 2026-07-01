from os import getenv

RABBIT_HOST = getenv("RABBIT_HOST", "rabbitmq")
RABBIT_PORT = int(getenv("RABBIT_PORT", "5672"))
RABBIT_USER = getenv("RABBIT_USER", "guest")
RABBIT_PASS = getenv("RABBIT_PASS", "guest")
EXCHANGE = getenv("EXCHANGE", "urbanhub")
BUFFER_SIZE = int(getenv("BUFFER_SIZE", "10"))