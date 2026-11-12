"""One structlog event per request, bound to the request id (spec section 14)."""

import hashlib
import json
import logging

import pytest
from fastapi.testclient import TestClient

from pain_demo.app import create_app
from pain_demo.settings import Settings


@pytest.fixture(autouse=True)
def quiet_test_client() -> None:
    """The test client logs its own requests at INFO through stdlib logging; keep them out of the captured output."""
    logging.getLogger("httpx2").setLevel(logging.WARNING)


def json_lines(captured: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in captured.splitlines() if line.strip()]


def test_json_format_emits_one_event_per_request(capsys: pytest.CaptureFixture[str]) -> None:
    with TestClient(create_app(Settings(log_format="json", log_level="INFO"))) as client:
        client.get("/api/v1/version", headers={"X-Request-Id": "req-log"})

    events = json_lines(capsys.readouterr().out)
    assert len(events) == 1
    (event,) = events
    assert event["event"] == "request"
    assert event["level"] == "info"
    assert event["request_id"] == "req-log"
    assert event["method"] == "GET"
    assert event["path"] == "/api/v1/version"
    assert event["status"] == 200
    assert isinstance(event["duration_ms"], int | float)
    assert "timestamp" in event


def test_health_checks_log_at_debug_only(capsys: pytest.CaptureFixture[str]) -> None:
    with TestClient(create_app(Settings(log_format="json", log_level="INFO"))) as client:
        client.get("/api/v1/health")
    assert json_lines(capsys.readouterr().out) == []

    with TestClient(create_app(Settings(log_format="json", log_level="DEBUG"))) as client:
        client.get("/api/v1/health")
    requests = [e for e in json_lines(capsys.readouterr().out) if e["logger"] == "pain_demo.request"]
    assert [(e["event"], e["level"], e["path"]) for e in requests] == [("request", "debug", "/api/v1/health")]


def test_errors_are_logged_with_their_status(capsys: pytest.CaptureFixture[str]) -> None:
    with TestClient(create_app(Settings(log_format="json", log_level="INFO"))) as client:
        client.get("/api/v1/missing", headers={"X-Request-Id": "req-missing"})

    (event,) = json_lines(capsys.readouterr().out)
    assert (event["status"], event["request_id"]) == (404, "req-missing")


def test_validation_requests_log_the_report_summary_but_never_the_content(capsys: pytest.CaptureFixture[str]) -> None:
    content = (
        b'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.02"><Nm>Secret Customer Ltd</Nm></Document>'
    )
    with TestClient(create_app(Settings(log_format="json", log_level="INFO"))) as client:
        client.post(
            "/api/v1/validations",
            files={"file": ("customer-batch.xml", content, "application/xml")},
        )

    out = capsys.readouterr().out
    (event,) = json_lines(out)
    assert event["status"] == 200
    assert event["message_version"] is None
    assert event["valid"] is False
    assert event["problem_count"] == 1
    assert event["problem_codes"] == ["unsupported_message"]
    assert event["size_bytes"] == len(content)
    assert event["sha256"] == hashlib.sha256(content).hexdigest()
    for leaked in ("Secret Customer", "customer-batch", "pain.001.001.02"):
        assert leaked not in out


def test_console_format_is_human_readable(capsys: pytest.CaptureFixture[str]) -> None:
    with TestClient(create_app(Settings(log_format="console", log_level="INFO"))) as client:
        client.get("/api/v1/version", headers={"X-Request-Id": "req-console"})

    out = capsys.readouterr().out
    assert "request" in out
    assert "req-console" in out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)


def test_uvicorn_loggers_join_the_structlog_pipeline(capsys: pytest.CaptureFixture[str]) -> None:
    create_app(Settings(log_format="json", log_level="INFO"))

    logging.getLogger("uvicorn.error").warning("Waiting for application startup.")
    logging.getLogger("uvicorn.access").info('"GET /api/v1/health HTTP/1.1" 200')

    events = json_lines(capsys.readouterr().out)
    assert [(e["event"], e["level"], e["logger"]) for e in events] == [
        ("Waiting for application startup.", "warning", "uvicorn.error")
    ]
