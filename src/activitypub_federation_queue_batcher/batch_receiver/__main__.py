import logging
import os
from base64 import b64decode
from datetime import UTC, datetime
from urllib.parse import urlunsplit

import aiohttp.web
import multidict

from activitypub_federation_queue_batcher._apub_helpers import (
    is_tolerable_activity_submission_status_code,
)
from activitypub_federation_queue_batcher._logging_helpers import setup_logging
from activitypub_federation_queue_batcher.types import (
    SerializableActivitySubmission,
    UpstreamSubmissionResponse,
)

logger = logging.getLogger(__name__)


AIOHTTP_CLIENTSESSION = aiohttp.web.AppKey(
    "AIOHTTP_CLIENTSESSION",
    aiohttp.ClientSession,
)


async def submit(
    cs: aiohttp.ClientSession,
    activity: SerializableActivitySubmission,
) -> UpstreamSubmissionResponse:
    req_headers: multidict.CIMultiDict[str] = multidict.CIMultiDict()
    for header in activity.headers:
        req_headers.add(header[0], header[1])

    url = urlunsplit(
        (
            os.environ.get("OVERRIDE_DESTINATION_PROTOCOL", "https"),
            os.environ.get("OVERRIDE_DESTINATION_DOMAIN", req_headers.getone("host")),
            activity.path,
            "",
            "",
        ),
    )

    now = datetime.now(UTC)
    submission_delay = now - activity.time

    logger.info(
        "Submitting activity id %s after a delay of %s",
        activity.activity_id,
        submission_delay,
    )

    async with cs.post(url, data=b64decode(activity.b64_body)) as resp:
        logger.info(
            "Got status %s for activity id %s",
            resp.status,
            activity.activity_id,
        )

        if not is_tolerable_activity_submission_status_code(resp.status):
            resp.raise_for_status()

        return UpstreamSubmissionResponse(
            time=datetime.now(UTC),
            activity_id=activity.activity_id,
            status=resp.status,
            headers=[[k, v] for k, v in resp.headers.items()],
            content_type=resp.headers.getone("content-type"),
            body=(await resp.text())
            if resp.content_length is not None and resp.content_length > 0
            else None,
        )


async def handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
    body = await request.read()

    activities: list[SerializableActivitySubmission] = (
        SerializableActivitySubmission.schema().loads(body, many=True)
    )

    responses = [
        await submit(request.app[AIOHTTP_CLIENTSESSION], activity)
        for activity in activities
    ]

    return aiohttp.web.json_response(
        text=UpstreamSubmissionResponse.schema().dumps(responses, many=True),
    )


async def init() -> aiohttp.web.Application:
    setup_logging()

    app = aiohttp.web.Application()
    app[AIOHTTP_CLIENTSESSION] = aiohttp.ClientSession()

    # just handle all paths in the same handler
    app.add_routes(
        [aiohttp.web.post(os.environ.get("BATCH_RECEIVER_PATH", "/batch"), handler)],
    )

    return app


if __name__ == "__main__":
    aiohttp.web.run_app(init())
