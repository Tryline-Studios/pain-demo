"""Per-request context: the request id and the one log event per request (spec sections 14.2 and 14.3)."""

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable, MutableMapping
from http import HTTPStatus
from typing import Any

import structlog
from starlette.datastructures import MutableHeaders
from starlette.requests import Request

type Scope = MutableMapping[str, Any]
type Message = MutableMapping[str, Any]
type Receive = Callable[[], Awaitable[Message]]
type Send = Callable[[Message], Awaitable[None]]
type ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

REQUEST_ID_HEADER = "X-Request-Id"
_ACCEPTABLE_REQUEST_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}")


def resolve_request_id(incoming: str | None) -> str:
    """Keep a caller's id when it is safe to log and echo; otherwise mint a UUID."""
    if incoming is not None and _ACCEPTABLE_REQUEST_ID.fullmatch(incoming):
        return incoming
    return str(uuid.uuid4())


def request_id_of(request: Request) -> str:
    return request.state.request_id


class RequestContextMiddleware:
    """Assigns every HTTP request an id, echoes it as a response header, binds it to every log line of the request
    and logs one `request` event when the response is done (at DEBUG for the paths in `quiet_paths`)."""

    def __init__(self, app: ASGIApp, quiet_paths: frozenset[str] = frozenset()) -> None:
        self.app = app
        self.quiet_paths = quiet_paths
        self.log = structlog.get_logger("pain_demo.request")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        scope.setdefault("state", {})["request_id"] = request_id
        status = HTTPStatus.INTERNAL_SERVER_ERROR.value
        started = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = MutableHeaders(scope=message)
                headers.setdefault(REQUEST_ID_HEADER, request_id)
            await send(message)

        with structlog.contextvars.bound_contextvars(request_id=request_id):
            try:
                await self.app(scope, receive, send_with_request_id)
            finally:
                level = logging.DEBUG if request.url.path in self.quiet_paths else logging.INFO
                self.log.log(
                    level,
                    "request",
                    method=request.method,
                    path=request.url.path,
                    status=status,
                    duration_ms=round((time.perf_counter() - started) * 1000, 1),
                )
