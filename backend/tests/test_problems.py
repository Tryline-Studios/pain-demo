"""Every error is RFC 9457 problem details, and `instance` carries the request id (spec section 12.3)."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from pain_demo.app import create_app

PROBLEM_JSON = "application/problem+json"


class ProbeHit(BaseModel):
    name_variant: str


class ProbeRequest(BaseModel):
    seed: str = Field(max_length=64)
    hits: list[ProbeHit] = []


def probe_app() -> FastAPI:
    """The app plus routes that provoke the errors under test."""
    app = create_app()

    @app.post("/api/v1/probe")
    def probe(request: ProbeRequest) -> ProbeRequest:
        return request

    @app.get("/api/v1/probe/boom")
    def boom() -> None:
        raise RuntimeError("boom")

    return app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(probe_app(), raise_server_exceptions=False) as client:
        yield client


def test_not_found_is_a_problem(client: TestClient) -> None:
    response = client.get("/api/v1/no-such-route", headers={"X-Request-Id": "req-404"})

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Not Found",
        "instance": "req-404",
    }


def test_validation_errors_replace_the_default_422_body(client: TestClient) -> None:
    response = client.post(
        "/api/v1/probe",
        json={"seed": "x" * 65, "hits": [{"name_variant": "primary"}, {}]},
        headers={"X-Request-Id": "req-422"},
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM_JSON
    body = response.json()
    assert body["type"] == "validation_error"
    assert body["title"] == "Validation error"
    assert body["status"] == 422
    assert body["instance"] == "req-422"
    assert body["errors"] == [
        {"field": "seed", "message": "String should have at most 64 characters", "code": "string_too_long"},
        {"field": "hits[1].name_variant", "message": "Field required", "code": "missing"},
    ]
    assert "detail" not in body or isinstance(body["detail"], str)


def test_unhandled_errors_are_problems_with_the_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/probe/boom", headers={"X-Request-Id": "req-500"})

    assert response.status_code == 500
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.headers["X-Request-Id"] == "req-500"
    assert response.json() == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "Internal Server Error",
        "instance": "req-500",
    }


ONE_MEGABYTE = 1024 * 1024


def test_a_body_over_one_megabyte_is_rejected_with_413(client: TestClient) -> None:
    response = client.post(
        "/api/v1/probe",
        content=b"x" * (ONE_MEGABYTE + 1),
        headers={"Content-Type": "application/json", "X-Request-Id": "req-413"},
    )

    assert response.status_code == 413
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json() == {
        "type": "about:blank",
        "title": "Content Too Large",
        "status": 413,
        "detail": "Request body exceeds 1 MB",
        "instance": "req-413",
    }


def test_an_oversized_body_is_rejected_even_when_the_route_never_reads_it(client: TestClient) -> None:
    response = client.request("GET", "/api/v1/health", content=b"x" * (ONE_MEGABYTE + 1))

    assert response.status_code == 413
    assert response.headers["content-type"] == PROBLEM_JSON


def test_a_chunked_body_over_one_megabyte_is_rejected_with_413(client: TestClient) -> None:
    def chunks() -> Iterator[bytes]:
        for _ in range(3):
            yield b"x" * (ONE_MEGABYTE // 2)

    response = client.post("/api/v1/probe", content=chunks(), headers={"Content-Type": "application/json"})

    assert response.status_code == 413
    assert response.json()["title"] == "Content Too Large"


def test_a_body_of_exactly_one_megabyte_is_accepted(client: TestClient) -> None:
    padding = b" " * (ONE_MEGABYTE - len(b'{"seed": "s"}'))

    response = client.post(
        "/api/v1/probe", content=b'{"seed": "s"}' + padding, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 200
