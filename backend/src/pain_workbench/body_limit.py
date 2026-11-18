"""Request bodies are capped at 1 MB, with per-path exceptions such as 10 MB for Upload Validation (spec section
12.4): larger ones get a 413 problem."""

from collections.abc import Mapping
from http import HTTPStatus

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from pain_workbench.problems import ProblemResponse, http_problem

MEGABYTE = 1024 * 1024
MAX_BODY_BYTES = MEGABYTE


def _detail(cap: int) -> str:
    return f"Request body exceeds {cap // MEGABYTE} MB"


class BodyTooLarge(HTTPException):
    """Raised from `receive` for a chunked body that grows past the cap, so it surfaces inside the route where the
    problem handlers see it."""

    def __init__(self, cap: int) -> None:
        super().__init__(HTTPStatus.CONTENT_TOO_LARGE, detail=_detail(cap))


class BodyLimitMiddleware:
    """Rejects a request whose declared Content-Length is over the cap before dispatch, and a chunked body as soon
    as it grows past the cap. `path_caps` raises the cap for the exact paths it names."""

    def __init__(self, app: ASGIApp, path_caps: Mapping[str, int] | None = None) -> None:
        self.app = app
        self.path_caps = path_caps or {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        cap = self.path_caps.get(request.url.path, MAX_BODY_BYTES)
        declared = request.headers.get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > cap:
            response = ProblemResponse(http_problem(request, HTTPStatus.CONTENT_TOO_LARGE, _detail(cap)))
            await response(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > cap:
                    raise BodyTooLarge(cap)
            return message

        await self.app(scope, limited_receive, send)
