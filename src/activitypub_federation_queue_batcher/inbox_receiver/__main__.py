import json
import logging
import os
from base64 import b64encode
from datetime import UTC, datetime

import aio_pika
import aiohttp.web

from activitypub_federation_queue_batcher._logging_helpers import setup_logging
from activitypub_federation_queue_batcher._rmq_helpers import (
    bootstrap,
    declare_activity_queue,
)
from activitypub_federation_queue_batcher.constants import (
    HTTP_BATCH_SIZE,
    RABBITMQ_CHANNEL_ROUTING_KEY,
)
from activitypub_federation_queue_batcher.types import SerializableActivitySubmission

logger = logging.getLogger(__name__)


RABBITMQ_CONNECTION_APP_KEY: aiohttp.web.AppKey[
    aio_pika.abc.AbstractRobustConnection
] = aiohttp.web.AppKey(
    "RABBITMQ_CONNECTION_APP_KEY",
    aio_pika.abc.AbstractRobustConnection,
)

MESSAGE_QUEUE_LIMIT = int(os.environ.get("MESSAGE_QUEUE_LIMIT", HTTP_BATCH_SIZE * 2))


async def handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
    async with request.app[RABBITMQ_CONNECTION_APP_KEY].channel(
        on_return_raises=True,
    ) as channel:
        queue = await declare_activity_queue(channel, passive=True)

        if (
            queue.declaration_result.message_count is not None
            and queue.declaration_result.message_count >= MESSAGE_QUEUE_LIMIT
        ):
            logger.info(
                "RabbitMQ has %s messages queued,"
                " deferring further requests until more buffer space is "
                "available",
                queue.declaration_result.message_count,
            )
            return aiohttp.web.HTTPServiceUnavailable()

        body = await request.read()

        activity_id = None
        try:
            j = json.loads(body)
            if "id" in j:
                logger.info("Queueing activity %s", j["id"])
                activity_id = j["id"]
            else:
                logger.warning("Missing activity id in JSON body")
        except Exception:
            logger.exception("Unable to parse request body as JSON")

        serializable_request = SerializableActivitySubmission(
            time=datetime.now(UTC),
            activity_id=activity_id,
            host=request.headers.getone("host"),
            path=request.path,
            headers=[[k, v] for k, v in request.headers.items()],
            b64_body=b64encode(body).decode(),
        )

        await channel.default_exchange.publish(
            aio_pika.Message(
                body=SerializableActivitySubmission.schema()
                .dumps(serializable_request)
                .encode(),
                delivery_mode=aio_pika.abc.DeliveryMode.PERSISTENT,
            ),
            routing_key=RABBITMQ_CHANNEL_ROUTING_KEY,
            timeout=5.0,
        )

    return aiohttp.web.HTTPNoContent()


async def init() -> aiohttp.web.Application:
    setup_logging()

    app = aiohttp.web.Application()

    app[RABBITMQ_CONNECTION_APP_KEY] = await aio_pika.connect_robust(
        host=os.environ.get("RABBITMQ_HOSTNAME", "localhost"),
    )
    await bootstrap(app[RABBITMQ_CONNECTION_APP_KEY])

    # just handle all paths in the same handler
    app.add_routes([aiohttp.web.post("/{path:.*}", handler)])

    return app


if __name__ == "__main__":
    aiohttp.web.run_app(init())
