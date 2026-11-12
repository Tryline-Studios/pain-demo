"""Goldens (spec 15.3): the clean request in all eleven Message Versions, byte-compared.

A golden changes only with the Generator Version: regenerate with `just goldens`, review the diff, and bump the app's
minor version in the same commit (spec 9.5).
"""

import json
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sample_files import assert_valid_sample_file

from pain_demo.app import create_app
from pain_demo.generation.sample_file import AnswerKey, answer_key_json
from pain_demo.settings import Settings
from pain_demo.validation import MESSAGE_VERSIONS

GOLDENS = Path(__file__).parent / "goldens"
UPDATE = os.environ.get("UPDATE_GOLDENS") == "1"

CLEAN_REQUEST = {
    "seed": "golden-clean",
    "created_at": "2026-01-02T09:00:00Z",
    "execution_date": "2026-01-05",
    "transaction_count": 10,
}
"""Hit Count 0 and Generated Data only; everything else is the defaults."""


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(create_app(Settings(git_sha="golden"))) as client:
        yield client


def golden(path: Path, actual: bytes) -> bytes:
    if UPDATE:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(actual)
    return path.read_bytes()


@pytest.mark.parametrize("message_version", MESSAGE_VERSIONS)
def test_the_clean_golden_is_reproduced_byte_for_byte(client: TestClient, message_version: str) -> None:
    response = client.post("/api/v1/sample-files", json={**CLEAN_REQUEST, "message_version": message_version})
    assert response.status_code == 200, response.text
    envelope = response.json()
    xml = envelope["sample_file"]["xml"].encode("utf-8")
    answer_key = answer_key_json(AnswerKey.model_validate(envelope["answer_key"])).encode("utf-8")

    assert xml == golden(GOLDENS / "clean" / f"{message_version}.xml", xml)
    assert answer_key == golden(GOLDENS / "clean" / f"{message_version}.answer-key.json", answer_key)
    assert_valid_sample_file(xml, message_version)


GOLDEN_FILES = sorted(GOLDENS.rglob("*.xml"))
"""Discovered, not listed, so every golden folder (clean, kitchen-sink, ...) is round-tripped."""


def test_goldens_are_discovered() -> None:
    assert {path.stem for path in GOLDEN_FILES} >= set(MESSAGE_VERSIONS), GOLDEN_FILES


@pytest.mark.parametrize("path", GOLDEN_FILES, ids=lambda path: str(path.relative_to(GOLDENS)))
def test_every_golden_passes_upload_validation(client: TestClient, path: Path) -> None:
    answer_key = json.loads(path.with_name(f"{path.stem}.answer-key.json").read_text("utf-8"))

    response = client.post(
        "/api/v1/validations", content=path.read_bytes(), headers={"content-type": "application/xml"}
    )

    assert response.status_code == 200, response.text
    report = response.json()
    assert report["valid"] is True, report["problems"]
    assert report["message_version"] == answer_key["message_version"]
    assert report["transaction_count"] == answer_key["file"]["transaction_count"]
