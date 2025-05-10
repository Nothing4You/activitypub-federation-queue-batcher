import os

BATCH_RECEIVER_PROTOCOL = os.environ.get("BATCH_RECEIVER_PROTOCOL", "https")
BATCH_RECEIVER_DOMAIN = os.environ.get("BATCH_RECEIVER_DOMAIN")
BATCH_RECEIVER_PATH = os.environ.get("BATCH_RECEIVER_PATH", "/batch")

HTTP_BATCH_AUTHORIZATION = os.environ.get("HTTP_BATCH_AUTHORIZATION")
if (
    HTTP_BATCH_AUTHORIZATION is not None
    and not HTTP_BATCH_AUTHORIZATION.lower().startswith(
        "bearer ",
    )
):
    HTTP_BATCH_AUTHORIZATION = f"Bearer {HTTP_BATCH_AUTHORIZATION}"

HTTP_ALLOWED_IPS = os.environ.get("HTTP_ALLOWED_IPS")
HTTP_BATCH_MAX_WAIT = int(os.environ.get("HTTP_BATCH_MAX_WAIT", "3"))
HTTP_BATCH_SIZE = int(os.environ.get("HTTP_BATCH_SIZE", "100"))
HTTP_TRUSTED_PROXIES = os.environ.get("HTTP_TRUSTED_PROXIES")
HTTP_USER_AGENT = os.environ.get(
    "HTTP_USER_AGENT",
    "ActivityPub-Federation-Queue-Batcher (+https://github.com/Nothing4You/activitypub-federation-queue-batcher)",
)

OVERRIDE_DESTINATION_PROTOCOL = os.environ.get("OVERRIDE_DESTINATION_PROTOCOL", "https")
OVERRIDE_DESTINATION_DOMAIN = os.environ.get("OVERRIDE_DESTINATION_DOMAIN")

INBOX_RECEIVER_MESSAGE_QUEUE_LIMIT = int(
    os.environ.get("INBOX_RECEIVER_MESSAGE_QUEUE_LIMIT", HTTP_BATCH_SIZE * 2),
)

RABBITMQ_HOSTNAME = os.environ.get("RABBITMQ_HOSTNAME", "localhost")
RABBITMQ_CHANNEL_ROUTING_KEY = os.environ.get(
    "RABBITMQ_CHANNEL_ROUTING_KEY",
    "apub-queue",
)

# https://www.w3.org/TR/activitypub/#server-to-server-interactions
VALID_ACTIVITY_CONTENT_TYPES = {
    "application/ld+json",
    "application/activity+json",
}
