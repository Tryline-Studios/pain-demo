import importlib.metadata
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from pain_workbench.app import create_app


def test_health_reports_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_reports_the_generator_version_block(client: TestClient) -> None:
    response = client.get("/api/v1/version")

    assert response.status_code == 200
    body = response.json()
    assert list(body) == [
        "app_version",
        "git_sha",
        "pain001",
        "faker",
        "schwifty",
        "iuliia",
        "rapidfuzz",
        "catalogue_snapshot",
    ]
    assert re.fullmatch(r"\d+\.\d+\.\d+", body["app_version"])
    assert re.fullmatch(r"[0-9a-f]{40}|unknown", body["git_sha"])
    for library in ("pain001", "faker", "schwifty", "iuliia", "rapidfuzz"):
        assert body[library] == importlib.metadata.version(library), library
    assert date.fromisoformat(body["catalogue_snapshot"])


def test_version_uses_the_configured_git_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAIN_WORKBENCH_GIT_SHA", "0123456789abcdef0123456789abcdef01234567")

    with TestClient(create_app()) as client:
        body = client.get("/api/v1/version").json()

    assert body["git_sha"] == "0123456789abcdef0123456789abcdef01234567"
