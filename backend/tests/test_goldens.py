"""Goldens (spec 15.3): the clean and kitchen-sink requests in all eleven Message Versions, byte-compared.

A golden changes only with the Generator Version: regenerate with `just goldens`, review the diff, and bump the app's
minor version in the same commit (spec 9.5).
"""

import json
import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import get_args

import pytest
from fastapi.testclient import TestClient
from sample_files import assert_valid_sample_file

from pain_demo.app import create_app
from pain_demo.catalogue.capabilities import NameVariant, Placement
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

KITCHEN_SINK_REQUEST = {
    "seed": "golden-kitchen-sink",
    "created_at": "2026-01-02T09:00:00Z",
    "execution_date": "2026-01-05",
    "transaction_count": 12,
    "hit_count": 12,
    "countries": ["GB", "DE", "FR", "US"],
    "currencies": ["GBP", "EUR", "USD", "CHF"],
    "exposure_count": 1,
    "hits": [
        {"entity": "rosneft", "placement": "debtor", "name_variant": "exact"},
        {"entity": "vtb-bank", "placement": "debtor_agent", "rendering_mode": "bic_only"},
        {
            "entity": "evraz-plc",
            "placement": "creditor",
            "name_variant": "transliteration",
            "transaction": 1,
            "with_controller": True,
        },
        {
            "entity": "gazprombank",
            "placement": "creditor_agent",
            "name_variant": "alias",
            "transaction": 2,
            "rendering_mode": "name_only",
        },
        {"entity": "igor-sechin", "placement": "ultimate_debtor", "name_variant": "native_script", "transaction": 3},
        {"entity": "sberbank", "placement": "intermediary_agent_1", "name_variant": "fuzzed", "transaction": 4},
        {"entity": "promsvyazbank", "placement": "intermediary_agent_2", "name_variant": "exact", "transaction": 4},
        {"entity": "bank-rossiya", "placement": "intermediary_agent_3", "name_variant": "alias", "transaction": 4},
        {"entity": "mahan-air", "placement": "remittance", "name_variant": "exact", "transaction": 5},
    ],
    "payment": {"payment_information_id": "PMTINF-KITCHEN-SINK", "debtor_account": {"iban": "GB82WEST12345698765432"}},
    "transactions": [
        {},
        {},
        {},
        {},
        {},
        {
            "creditor": {"name": "Supplied Creditor Ltd"},
            "amount": "1234.56",
            "currency": "GBP",
            "remittance": {"unstructured": ["Invoice 42"]},
        },
    ],
}
"""Named Hits pin every Placement, Name Variant and rendering mode and a controller pair, so coverage does not hang on
a lucky Seed; two more Hits are drawn. Partial JSON Supplied Data, four countries and currencies, one Exposure."""

REQUESTS = {"clean": CLEAN_REQUEST, "kitchen-sink": KITCHEN_SINK_REQUEST}


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
@pytest.mark.parametrize("name", REQUESTS)
def test_each_golden_is_reproduced_byte_for_byte(client: TestClient, name: str, message_version: str) -> None:
    response = client.post("/api/v1/sample-files", json={**REQUESTS[name], "message_version": message_version})
    assert response.status_code == 200, response.text
    envelope = response.json()
    xml = envelope["sample_file"]["xml"].encode("utf-8")
    answer_key = answer_key_json(AnswerKey.model_validate(envelope["answer_key"])).encode("utf-8")

    assert xml == golden(GOLDENS / name / f"{message_version}.xml", xml)
    assert answer_key == golden(GOLDENS / name / f"{message_version}.answer-key.json", answer_key)
    assert_valid_sample_file(xml, message_version)


GOLDEN_FILES = sorted(GOLDENS.rglob("*.xml"))
"""Discovered, not listed, so every golden folder (clean, kitchen-sink, ...) is round-tripped."""


def test_goldens_are_discovered() -> None:
    assert len(GOLDEN_FILES) == len(REQUESTS) * len(MESSAGE_VERSIONS), GOLDEN_FILES


@pytest.mark.parametrize("message_version", MESSAGE_VERSIONS)
def test_the_kitchen_sink_covers_everything_it_promises(message_version: str) -> None:
    folder = GOLDENS / "kitchen-sink"
    answer_key = json.loads((folder / f"{message_version}.answer-key.json").read_text("utf-8"))
    xml = (folder / f"{message_version}.xml").read_text("utf-8")
    hits = answer_key["hits"]

    assert {hit["placement"] for hit in hits} == set(get_args(Placement.__value__))
    assert {hit["name"]["variant"] for hit in hits if hit["name"]} == set(get_args(NameVariant.__value__))
    assert {hit.get("rendering_mode") for hit in hits} >= {"bic_only", "name_only"}
    assert any(hit["paired_with"] for hit in hits)
    assert {hit["origin"] for hit in hits} == {"named", "drawn"}
    assert len(answer_key["exposures"]) >= 1
    assert answer_key["request"]["payment"]
    assert answer_key["request"]["transactions"]
    assert "Supplied Creditor Ltd" in xml
    assert len(set(re.findall(r'Ccy="([A-Z]{3})"', xml))) >= 3
    assert len(set(re.findall(r"<Ctry>([A-Z]{2})</Ctry>", xml))) >= 3


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
