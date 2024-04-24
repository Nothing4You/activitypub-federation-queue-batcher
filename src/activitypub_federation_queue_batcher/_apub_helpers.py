from aiohttp.web import (
    HTTPBadRequest,
    HTTPInternalServerError,
    HTTPRequestTimeout,
    HTTPTooManyRequests,
)


def is_permanent_activity_submission_failure(status: int, /) -> bool:
    return (
        HTTPBadRequest.status_code <= status < HTTPInternalServerError.status_code
        and status
        not in (HTTPRequestTimeout.status_code, HTTPTooManyRequests.status_code)
    )


def is_tolerable_activity_submission_status_code(status: int, /) -> bool:
    return (
        status not in (HTTPRequestTimeout.status_code, HTTPTooManyRequests.status_code)
        and status < HTTPInternalServerError.status_code
    )
