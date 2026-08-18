"""Decorator making MCP tool failures visible in the logs."""

import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger("hbg.tool")

F = TypeVar("F", bound=Callable[..., Any])


def log_tool_errors(func: F) -> F:
    """Log calls to an MCP tool, plus any exception with its full traceback.

    FastMCP catches tool exceptions and turns them into an error *result* over a
    HTTP 200 response, so without this the failure would never reach error.log.
    The exception is re-raised, leaving the MCP error response unchanged.

    Apply below `@mcp.tool()`:

        @mcp.tool()
        @log_tool_errors
        async def my_tool(...): ...
    """
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.info("Tool %s called", func.__name__)
            try:
                return await func(*args, **kwargs)
            except Exception:
                logger.exception("Tool %s failed", func.__name__)
                raise

        return async_wrapper  # type: ignore[return-value]

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger.info("Tool %s called", func.__name__)
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception("Tool %s failed", func.__name__)
            raise

    return wrapper  # type: ignore[return-value]
