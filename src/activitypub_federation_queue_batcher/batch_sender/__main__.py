import asyncio
import logging
import sys
from datetime import UTC, datetime, timedelta
from urllib.parse import urlunsplit

import aio_pika
import aiohttp.client
from aio_pika.abc import AbstractIncomingMessage
from multidict import istr

from activitypub_federation_queue_batcher._apub_helpers import (
    is_tolerable_activity_submission_status_code,
)
from activitypub_federation_queue_batcher._logging_helpers import setup_logging
from activitypub_federation_queue_batcher._rmq_helpers import (
    bootstrap_rmq,
    declare_activity_queue,
)
from activitypub_federation_queue_batcher.constants import (
    BATCH_RECEIVER_DOMAIN,
    BATCH_RECEIVER_PATH,
    BATCH_RECEIVER_PROTOCOL,
    HTTP_BATCH_AUTHORIZATION,
    HTTP_BATCH_MAX_WAIT,
    HTTP_BATCH_SIZE,
    HTTP_USER_AGENT,
)
from activitypub_federation_queue_batcher.types import (
    SerializableActivitySubmission,
    UpstreamSubmissionResponse,
)

logger = logging.getLogger(__name__)


async def get_rmq_messages(
    queue: aio_pika.abc.AbstractQueue,
    limit: int,
    timeout: float,
) -> list[AbstractIncomingMessage]:
    max_wait_until = None

    messages: list[AbstractIncomingMessage] = []
    while len(messages) == 0 or (
        len(messages) < limit
        and max_wait_until is not None
        and datetime.now(UTC) < max_wait_until
    ):
        consume_timeout = (
            None
            if max_wait_until is None
            # TODO: Check if this is a known mypy issue, otherwise raise with them
            else (max_wait_until - datetime.now(UTC)).total_seconds()  # type: ignore[operator]
        )

        # We want to get up to `limit` messages instead of just taking as many as we
        # can get from the server.
        # See also https://github.com/mosquito/aio-pika/issues/131
        msg = await queue.get(fail=False, timeout=consume_timeout)

        if msg is None:
            if len(messages) > 0:
                return messages

            await asyncio.sleep(0.1)
            continue

        messages.append(msg)

        if max_wait_until is None and len(messages) > 0 and limit > 1:
            max_wait_until = datetime.now(UTC) + timedelta(seconds=timeout)

    return messages


def get_batch_request_headers() -> dict[istr, str]:
    headers = {
        aiohttp.hdrs.USER_AGENT: HTTP_USER_AGENT,
        aiohttp.hdrs.CONTENT_TYPE: "application/json",
    }

    if HTTP_BATCH_AUTHORIZATION is not None:
        headers[aiohttp.hdrs.AUTHORIZATION] = HTTP_BATCH_AUTHORIZATION

    return headers


async def requeue_messages(messages: list[AbstractIncomingMessage]) -> None:
    # This ensures that all messages we previously started processing are
    # returned to the queue
    await messages[-1].nack(multiple=True, requeue=True)

    # TODO: Figure out how we can ensure ordered queue if we have buffered
    #  messages when requeueing nack'ed messages
    sys.exit(1)


def is_acceptable_batch_entry(
    index: int,
    activity: SerializableActivitySubmission,
    response: UpstreamSubmissionResponse,
) -> bool:
    if activity.activity_id != response.activity_id:
        logger.error(
            "Activity id mismatch at index %s: %s != %s",
            index,
            activity.activity_id,
            response.activity_id,
        )
        return False

    if not is_tolerable_activity_submission_status_code(
        response.status,
    ):
        logger.warning(
            "Activity %s at index %s failed with status code: %s",
            activity.activity_id,
            index,
            response.status,
        )
        return False

    return True


async def forwarder() -> None:
    if BATCH_RECEIVER_DOMAIN is None or len(BATCH_RECEIVER_DOMAIN) == 0:
        logger.error("BATCH_RECEIVER_DOMAIN must be set")
        sys.exit(1)

    rmq = await bootstrap_rmq()

    url = urlunsplit(
        (
            BATCH_RECEIVER_PROTOCOL,
            BATCH_RECEIVER_DOMAIN,
            BATCH_RECEIVER_PATH,
            "",
            "",
        ),
    )

    headers = get_batch_request_headers()

    async with rmq.channel() as channel, aiohttp.ClientSession() as cs:
        await channel.set_qos(prefetch_count=HTTP_BATCH_SIZE)
        queue = await declare_activity_queue(channel)

        while True:
            messages = await get_rmq_messages(
                queue,
                HTTP_BATCH_SIZE,
                HTTP_BATCH_MAX_WAIT,
            )

            if len(messages) == 0:
                logger.warning("Ended up with zero messages, how??")
                continue

            logger.info("Processing batch of %s messages", len(messages))

            activities: list[SerializableActivitySubmission] = []

            for msg in messages:
                activity: SerializableActivitySubmission = (
                    # TODO: Figure out if this type check is fixable
                    SerializableActivitySubmission.schema().loads(  # type: ignore[assignment]
                        msg.body.decode(),
                    )
                )
                logger.info("Including activity %s in batch", activity.activity_id)
                activities.append(activity)

            body = (
                SerializableActivitySubmission.schema()
                .dumps(activities, many=True)
                .encode()
            )

            async with cs.post(url, headers=headers, data=body) as resp:
                resp.raise_for_status()
                t = await resp.text()

            responses: list[UpstreamSubmissionResponse] = (
                UpstreamSubmissionResponse.schema().loads(t, many=True)
            )

            if len(responses) != len(messages):
                logger.warning(
                    "Batch response count does not match message count: %s != %s",
                    len(responses),
                    len(messages),
                )

            activities_ok = 0
            async with asyncio.TaskGroup() as tg:
                for i in range(len(messages)):
                    try:
                        if not is_acceptable_batch_entry(
                            i,
                            activities[i],
                            responses[i],
                        ):
                            break

                        tg.create_task(messages[i].ack())
                        activities_ok += 1
                    except IndexError:
                        break

            if activities_ok < len(messages):
                await requeue_messages(messages[activities_ok:])

            logger.info("Finished batch of %s messages", len(messages))


async def main() -> None:
    setup_logging()
    await forwarder()


if __name__ == "__main__":
    asyncio.run(main())
