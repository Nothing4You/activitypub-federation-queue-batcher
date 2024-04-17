def is_tolerable_activity_submission_status_code(status: int, /) -> bool:
    return status in (408, 429) or status >= 500  # noqa: PLR2004
