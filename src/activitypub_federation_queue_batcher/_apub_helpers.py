def is_tolerable_activity_submission_status_code(status: int, /) -> bool:
    return status not in (408, 429) and status < 500  # noqa: PLR2004
