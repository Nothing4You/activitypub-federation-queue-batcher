import logging
from base64 import b64decode
from datetime import UTC, datetime
from urllib.parse import urlunsplit

import aiohttp.web
import multidict

from activitypub_federation_queue_batcher._aiohttp_helpers import (
    ALLOWED_IPS_APP_KEY,
    is_allowed_ip,
    parse_trusted_ips,
)
from activitypub_federation_queue_batcher._apub_helpers import (
    is_permanent_activity_submission_failure,
    is_tolerable_activity_submission_status_code,
)
from activitypub_federation_queue_batcher._logging_helpers import setup_logging
from activitypub_federation_queue_batcher.constants import (
    BATCH_RECEIVER_PATH,
    HTTP_ALLOWED_IPS,
    HTTP_BATCH_AUTHORIZATION,
    HTTP_TRUSTED_PROXIES,
    OVERRIDE_DESTINATION_DOMAIN,
    OVERRIDE_DESTINATION_PROTOCOL,
)
from activitypub_federation_queue_batcher.types import (
    SerializableActivitySubmission,
    UpstreamSubmissionResponse,
)

if HTTP_TRUSTED_PROXIES is not None:
    import aiohttp_remotes

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
            OVERRIDE_DESTINATION_PROTOCOL,
            OVERRIDE_DESTINATION_DOMAIN
            if OVERRIDE_DESTINATION_DOMAIN is not None
            else req_headers.getone(aiohttp.hdrs.HOST),
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

    async with cs.post(
        url,
        data=b64decode(activity.b64_body),
        headers=req_headers,
    ) as resp:
        body = (
            await resp.text()
            if resp.content_length is not None and resp.content_length > 0
            else None
        )

        usr = UpstreamSubmissionResponse(
            time=datetime.now(UTC),
            activity_id=activity.activity_id,
            status=resp.status,
            headers=[[k, v] for k, v in resp.headers.items()],
            content_type=resp.headers.get(aiohttp.hdrs.CONTENT_TYPE),
            body=body,
        )

        if is_permanent_activity_submission_failure(resp.status):
            logger.warning(
                "Got status %s for activity id %s",
                resp.status,
                activity.activity_id,
            )
            logger.warning(
                "Activity %s request: %s",
                activity.activity_id,
                SerializableActivitySubmission.schema().dumps(activity),
            )
            logger.warning(
                "Activity %s response: %s",
                activity.activity_id,
                UpstreamSubmissionResponse.schema().dumps(usr),
            )
        else:
            logger.info(
                "Got status %s for activity id %s",
                resp.status,
                activity.activity_id,
            )

        return usr


async def handler(request: aiohttp.web.Request) -> aiohttp.web.Response:
    if ALLOWED_IPS_APP_KEY in request.app:
        if request.remote is None:
            logger.warning("Allowed IPs configured but source IP was None")
            raise aiohttp.web.HTTPServiceUnavailable

        if not is_allowed_ip(
            allowed_ips=request.app[ALLOWED_IPS_APP_KEY],
            client_ip=request.remote,
        ):
            logger.info("Allowed IPs configured but %r is not allowed", request.remote)
            raise aiohttp.web.HTTPServiceUnavailable(text="Source IP not permitted")

    if HTTP_BATCH_AUTHORIZATION is not None and (
        request.headers.get(aiohttp.hdrs.AUTHORIZATION) != HTTP_BATCH_AUTHORIZATION
    ):
        return aiohttp.web.HTTPUnauthorized(text="Missing authorization header")

    body = await request.read()

    activities: list[SerializableActivitySubmission] = (
        SerializableActivitySubmission.schema().loads(body, many=True)
    )

    responses = []

    for activity in activities:
        resp = await submit(request.app[AIOHTTP_CLIENTSESSION], activity)
        responses.append(resp)

        if not is_tolerable_activity_submission_status_code(resp.status):
            break

    return aiohttp.web.json_response(
        text=UpstreamSubmissionResponse.schema().dumps(responses, many=True),
    )


async def init() -> aiohttp.web.Application:
    setup_logging()

    app = aiohttp.web.Application(
        # set body size limit to 20MB to allow processing large batches
        client_max_size=20 * (1024**2),
    )
    app[AIOHTTP_CLIENTSESSION] = aiohttp.ClientSession()

    # just handle all paths in the same handler
    app.add_routes(
        [aiohttp.web.post(BATCH_RECEIVER_PATH, handler)],
    )

    if HTTP_TRUSTED_PROXIES is not None:
        await aiohttp_remotes.setup(
            app,
            aiohttp_remotes.XForwardedFiltered(
                trusted=HTTP_TRUSTED_PROXIES.split(","),
            ),
        )

    if HTTP_ALLOWED_IPS is not None:
        app[ALLOWED_IPS_APP_KEY] = parse_trusted_ips(HTTP_ALLOWED_IPS)

    return app


if __name__ == "__main__":
    aiohttp.web.run_app(init())
