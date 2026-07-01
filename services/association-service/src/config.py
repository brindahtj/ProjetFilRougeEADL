from os import getenv

RABBIT_HOST = getenv("RABBIT_HOST", "rabbitmq")
RABBIT_USER = getenv("RABBIT_USER", "guest")
RABBIT_PASS = getenv("RABBIT_PASS", "guest")
EXCHANGE = getenv("EXCHANGE", "urbanhub")

# Buffer size before triggering association
BUFFER_SIZE = int(getenv("BUFFER_SIZE", "10"))

# Time window (minutes) to associate measurements from same zone
TIME_WINDOW_MINUTES = int(getenv("TIME_WINDOW_MINUTES", "5"))