"""Logging setup: ISO 8601 UTC timestamps, split app/error log files.

Two file handlers are attached to the root logger:
    - app.log   — rotating, everything below ERROR
    - error.log — non-rotating, ERROR and above including full tracebacks
"""

import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path

APP_LOG_FILENAME = "app.log"
ERROR_LOG_FILENAME = "error.log"

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"

_MARKER = "_hbg_logging_handler"


class UTCISO8601Formatter(logging.Formatter):
    """Renders record timestamps as ISO 8601 in UTC, e.g. 2026-08-17T14:03:21.482Z."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


class BelowErrorFilter(logging.Filter):
    """Passes records below ERROR, keeping them out of the error log."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < logging.ERROR


def setup_logging(
    log_dir: str = "logs",
    level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    console: bool = True,
) -> None:
    """Configure the root logger. Safe to call more than once — later calls are no-ops."""
    root = logging.getLogger()

    if any(getattr(handler, _MARKER, False) for handler in root.handlers):
        return

    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)

    formatter = UTCISO8601Formatter(LOG_FORMAT)

    app_handler = logging.handlers.RotatingFileHandler(
        directory / APP_LOG_FILENAME,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.NOTSET)
    app_handler.addFilter(BelowErrorFilter())

    error_handler = logging.FileHandler(
        directory / ERROR_LOG_FILENAME,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)

    handlers: list[logging.Handler] = [app_handler, error_handler]

    if console:
        handlers.append(logging.StreamHandler())

    for handler in handlers:
        handler.setFormatter(formatter)
        setattr(handler, _MARKER, True)
        root.addHandler(handler)

    root.setLevel(level.upper())
