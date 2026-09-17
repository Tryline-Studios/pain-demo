import uuid

from fastapi.testclient import TestClient


def test_generates_a_uuid_request_id_when_none_is_sent(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert uuid.UUID(response.headers["X-Request-Id"]).version == 4


def test_echoes_the_request_id_the_caller_sent(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-Id": "regression-run-42"})

    assert response.headers["X-Request-Id"] == "regression-run-42"


def test_replaces_an_unusable_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-Id": "not a request id\t" + "x" * 200})

    assert uuid.UUID(response.headers["X-Request-Id"])


def test_error_responses_carry_the_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/no-such-route", headers={"X-Request-Id": "abc-123"})

    assert response.status_code == 404
    assert response.headers["X-Request-Id"] == "abc-123"
