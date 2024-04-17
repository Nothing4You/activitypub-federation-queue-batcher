import os

HTTP_BATCH_SIZE = int(os.environ.get("HTTP_BATCH_SIZE", 100))
HTTP_BATCH_MAX_WAIT = int(os.environ.get("HTTP_BATCH_MAX_WAIT", 3))
RABBITMQ_CHANNEL_ROUTING_KEY = os.environ.get(
    "RABBITMQ_CHANNEL_ROUTING_KEY",
    "apub-queue",
)
