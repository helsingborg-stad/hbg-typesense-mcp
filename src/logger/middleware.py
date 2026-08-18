"""ASGI middleware logging every HTTP request with its response status code."""

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger("hbg.request")

Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


class RequestLoggingMiddleware:
    """Logs `METHOD /path <status> <duration>` for each request.

    5xx responses and unhandled exceptions are logged at ERROR level so they
    land in error.log, exceptions with their full traceback.
    """

    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "-")
        target = scope.get("path", "-")
        query = scope.get("query_string", b"").decode("latin-1")
        if query:
            target = f"{target}?{query}"
        client = scope.get("client")
        client_host = client[0] if client else "-"

        status: int | None = None
        started = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception(
                "%s %s %s %.1fms client=%s unhandled exception",
                method,
                target,
                status if status is not None else 500,
                (time.perf_counter() - started) * 1000,
                client_host,
            )
            raise

        logger.log(
            logging.ERROR if status is not None and status >= 500 else logging.INFO,
            "%s %s %s %.1fms client=%s",
            method,
            target,
            status if status is not None else "-",
            (time.perf_counter() - started) * 1000,
            client_host,
        )
