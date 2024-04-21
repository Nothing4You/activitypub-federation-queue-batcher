import json
import logging
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
    MESSAGE_QUEUE_LIMIT,
    RABBITMQ_CHANNEL_ROUTING_KEY,
    RABBITMQ_HOSTNAME,
    VALID_ACTIVITY_CONTENT_TYPES,
)
from activitypub_federation_queue_batcher.types import SerializableActivitySubmission

logger = logging.getLogger(__name__)


RABBITMQ_CONNECTION_APP_KEY: aiohttp.web.AppKey[
    aio_pika.abc.AbstractRobustConnection
] = aiohttp.web.AppKey(
    "RABBITMQ_CONNECTION_APP_KEY",
    aio_pika.abc.AbstractRobustConnection,
)


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

        if request.content_type not in VALID_ACTIVITY_CONTENT_TYPES:
            logger.info("Received invalid content-type header %r", request.content_type)
            return aiohttp.web.HTTPUnsupportedMediaType(
                text="Invalid content-type header",
            )

        body = await request.read()

        try:
            j = json.loads(body)
        except json.JSONDecodeError:
            logger.info("Received invalid JSON body")
            return aiohttp.web.HTTPUnsupportedMediaType(text="Body is not JSON")

        activity_id = None
        if "id" in j:
            logger.info("Queueing activity %s", j["id"])
            activity_id = j["id"]
        else:
            logger.warning("Missing activity id in JSON body")
            return aiohttp.web.HTTPServiceUnavailable(
                text="Missing activity id in JSON body",
            )

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
        host=RABBITMQ_HOSTNAME,
    )
    await bootstrap(app[RABBITMQ_CONNECTION_APP_KEY])

    # just handle all paths in the same handler
    app.add_routes([aiohttp.web.post("/{path:.*}", handler)])

    return app


if __name__ == "__main__":
    aiohttp.web.run_app(init())
