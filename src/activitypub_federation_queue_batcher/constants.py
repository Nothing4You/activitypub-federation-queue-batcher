import os

HTTP_BATCH_SIZE = int(os.environ.get("HTTP_BATCH_SIZE", 100))
HTTP_BATCH_MAX_WAIT = int(os.environ.get("HTTP_BATCH_MAX_WAIT", 3))
MESSAGE_QUEUE_LIMIT = int(os.environ.get("MESSAGE_QUEUE_LIMIT", HTTP_BATCH_SIZE * 2))
RABBITMQ_CHANNEL_ROUTING_KEY = os.environ.get(
    "RABBITMQ_CHANNEL_ROUTING_KEY",
    "apub-queue",
)

# https://www.w3.org/TR/activitypub/#server-to-server-interactions
VALID_ACTIVITY_CONTENT_TYPES = {
    " application/ld+json",
    "application/activity+json",
}
