from aio_pika.abc import (
    AbstractChannel,
    AbstractQueue,
    AbstractRobustConnection,
)

from activitypub_federation_queue_batcher.constants import RABBITMQ_CHANNEL_ROUTING_KEY


async def declare_activity_queue(
    channel: AbstractChannel,
    *,
    passive: bool = False,
) -> AbstractQueue:
    return await channel.declare_queue(
        name=RABBITMQ_CHANNEL_ROUTING_KEY,
        durable=True,
        exclusive=False,
        auto_delete=False,
        passive=passive,
    )


async def bootstrap(connection: AbstractRobustConnection) -> None:
    async with connection.channel() as channel:
        await declare_activity_queue(channel)
