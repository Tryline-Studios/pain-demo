"""RFC 9457 problem details for every error response (spec section 12.3)."""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from pain_demo.request_context import REQUEST_ID_HEADER, add_log_fields, request_id_of

PROBLEM_MEDIA_TYPE = "application/problem+json"
ABOUT_BLANK = "about:blank"

# The request locations FastAPI prefixes to a validation error's location; the `field` path drops them.
_LOCATION_ROOTS = frozenset({"body", "query", "path", "header", "cookie"})


class Problem(BaseModel):
    """A problem details body. `type` is `about:blank` for plain HTTP errors and a stable token otherwise."""

    type: str = ABOUT_BLANK
    title: str
    status: int
    detail: str
    instance: str


class FieldError(BaseModel):
    field: str
    message: str
    code: str


class RequestValidationProblem(Problem):
    """`type` is `validation_error`; `field` is a dotted path into the request model, e.g. `hits[2].name_variant`."""

    type: str = "validation_error"
    title: str = "Validation error"
    status: int = HTTPStatus.UNPROCESSABLE_CONTENT
    errors: list[FieldError]


class BuildFailed(Exception):
    """The renderer's own output failed the XSD or dropped a Placement (spec 10.4); `detail` carries the reasons."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ProblemResponse(JSONResponse):
    media_type = PROBLEM_MEDIA_TYPE

    def __init__(self, problem: Problem, headers: Mapping[str, str] | None = None) -> None:
        super().__init__(
            problem.model_dump(mode="json"),
            status_code=problem.status,
            headers={REQUEST_ID_HEADER: problem.instance, **(headers or {})},
        )


def field_path(location: tuple[int | str, ...]) -> str:
    """`("body", "hits", 2, "name_variant")` becomes `hits[2].name_variant`."""
    parts = location[1:] if location and location[0] in _LOCATION_ROOTS else location
    path = ""
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else (f".{part}" if path else part)
    return path


def field_errors(errors: list[dict[str, Any]]) -> list[FieldError]:
    return [FieldError(field=field_path(tuple(e["loc"])), message=e["msg"], code=e["type"]) for e in errors]


def http_problem(request: Request, status: int, detail: str | None = None) -> Problem:
    phrase = HTTPStatus(status).phrase
    return Problem(title=phrase, status=status, detail=detail or phrase, instance=request_id_of(request))


async def handle_http_exception(request: Request, exc: Exception) -> ProblemResponse:
    assert isinstance(exc, HTTPException)  # noqa: S101 - narrowing FastAPI's untyped handler signature
    detail = exc.detail if isinstance(exc.detail, str) else None
    return ProblemResponse(http_problem(request, exc.status_code, detail), headers=exc.headers)


async def handle_validation_error(request: Request, exc: Exception) -> ProblemResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    errors = field_errors(list(exc.errors()))
    add_log_fields(request, outcome="validation_error")
    problem = RequestValidationProblem(
        detail=f"{len(errors)} field{'s' if len(errors) != 1 else ''} failed validation",
        instance=request_id_of(request),
        errors=errors,
    )
    return ProblemResponse(problem)


async def handle_build_failed(request: Request, exc: Exception) -> ProblemResponse:
    assert isinstance(exc, BuildFailed)  # noqa: S101
    problem = Problem(
        type="build_failed",
        title="Build failed",
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        detail=exc.detail,
        instance=request_id_of(request),
    )
    return ProblemResponse(problem)


async def handle_unexpected_error(request: Request, exc: Exception) -> ProblemResponse:
    return ProblemResponse(http_problem(request, HTTPStatus.INTERNAL_SERVER_ERROR))


def install_problem_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(BuildFailed, handle_build_failed)
    app.add_exception_handler(Exception, handle_unexpected_error)
