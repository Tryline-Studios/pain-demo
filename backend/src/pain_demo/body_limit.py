"""Request bodies are capped at 1 MB (spec section 12.4): larger ones get a 413 problem."""

from http import HTTPStatus

from starlette.exceptions import HTTPException
from starlette.requests import Request

from pain_demo.request_context import ASGIApp, Message, Receive, Scope, Send

MAX_BODY_BYTES = 1024 * 1024


class BodyTooLarge(HTTPException):
    """Raised from `receive`, so it surfaces inside the route where the problem handlers see it."""

    def __init__(self) -> None:
        super().__init__(HTTPStatus.CONTENT_TOO_LARGE, detail="Request body exceeds 1 MB")


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = Request(scope).headers.get("content-length")
        declared_too_large = declared is not None and declared.isdigit() and int(declared) > self.max_bytes
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            if declared_too_large:
                raise BodyTooLarge
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise BodyTooLarge
            return message

        await self.app(scope, limited_receive, send)
