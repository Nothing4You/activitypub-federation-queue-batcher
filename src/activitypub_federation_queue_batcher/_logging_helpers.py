import logging
import os
from datetime import UTC, datetime

EXTRA_LOGGER_CONFIGS = {
    "aiormq",
    "aio_pika",
}


def setup_logging() -> None:
    root_level = os.environ.get("LOGLEVEL", "INFO").upper()
    logging.basicConfig(
        level=root_level,
        format="%(asctime)s - %(levelname)8s - %(name)s:%(funcName)s - %(message)s",
    )

    logging.Formatter.formatTime = (  # type: ignore[method-assign]
        lambda self, record, datefmt: datetime.fromtimestamp(  # type: ignore[assignment,misc] # noqa: ARG005
            record.created,
            UTC,
        )
        .astimezone()
        .isoformat()
    )

    log_levels = logging.getLevelNamesMapping()
    for extra_logger in EXTRA_LOGGER_CONFIGS:
        level = os.environ.get(f"LOGLEVEL_{extra_logger.upper()}")

        if level is None:
            if log_levels[root_level] < logging.INFO:
                logging.getLogger(extra_logger).setLevel(logging.INFO)

            continue

        if level.upper() not in log_levels:
            logging.getLogger(__name__).warning(
                "Ignoring invalid log level %s for %s",
                level,
                extra_logger,
            )
            continue

        logging.getLogger(extra_logger).setLevel(level.upper())
