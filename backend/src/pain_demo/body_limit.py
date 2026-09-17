"""Request bodies are capped at 1 MB (spec section 12.4): larger ones get a 413 problem."""

from http import HTTPStatus

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from pain_demo.problems import ProblemResponse, http_problem

MAX_BODY_BYTES = 1024 * 1024
DETAIL = "Request body exceeds 1 MB"


class BodyTooLarge(HTTPException):
    """Raised from `receive` for a chunked body that grows past the cap, so it surfaces inside the route where the
    problem handlers see it."""

    def __init__(self) -> None:
        super().__init__(HTTPStatus.CONTENT_TOO_LARGE, detail=DETAIL)


class BodyLimitMiddleware:
    """Rejects a request whose declared Content-Length is over the cap before dispatch, and a chunked body as soon
    as it grows past the cap."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        declared = request.headers.get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
            response = ProblemResponse(http_problem(request, HTTPStatus.CONTENT_TOO_LARGE, DETAIL))
            await response(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_BODY_BYTES:
                    raise BodyTooLarge
            return message

        await self.app(scope, limited_receive, send)
