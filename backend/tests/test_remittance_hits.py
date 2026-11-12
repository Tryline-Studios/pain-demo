"""Remittance mention Placement (spec 6.7, 11.3): a drawn Hit's name inside a transaction's remittance information."""

from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sample_files import resolve
from test_catalogue import MINIMAL_BANK, write_catalogue
from test_drawn_hits import CATALOGUE, PMT_INF, generate, tree

from pain_demo.app import create_app
from pain_demo.validation import MESSAGE_VERSIONS

ELEMENT_PATHS = {
    "ustrd": "RmtInf/Ustrd",
    "addtl_rmt_inf": "RmtInf/Strd/AddtlRmtInf",
    "invcr": "RmtInf/Strd/Invcr/Nm",
    "invcee": "RmtInf/Strd/Invcee/Nm",
}


@pytest.fixture(scope="module")
def mentions() -> list[tuple[dict, dict]]:
    """Remittance Hits with their envelopes, over enough files to see every element."""
    with TestClient(create_app()) as client:
        envelopes = [
            generate(client, seed=f"remit-{n}", transaction_count=100, hit_count=100, message_version=version)
            for n, version in enumerate(MESSAGE_VERSIONS)
        ]
    return [(e, hit) for e in envelopes for hit in e["answer_key"]["hits"] if hit["placement"] == "remittance"]


def test_a_remittance_mention_names_the_entity_in_the_element_the_answer_key_records(
    mentions: list[tuple[dict, dict]],
) -> None:
    assert {hit["element"] for _, hit in mentions} == set(ELEMENT_PATHS)
    for envelope, hit in mentions:
        number = hit["transaction_number"]
        assert hit["xpath"] == f"{PMT_INF}/CdtTrfTxInf[{number}]/{ELEMENT_PATHS[hit['element']]}"
        (element,) = resolve(tree(envelope), hit["xpath"])
        text, name = str(element.text), hit["name"]["rendered"]
        if hit["element"] in {"invcr", "invcee"}:
            assert text == name
        else:  # a seeded sentence around the name, Max140Text
            assert name in text
            assert text != name
            assert len(text) <= 140
        assert name in [n.value for n in CATALOGUE.entities[hit["entity"]["id"]].names]
        for absent in ("rendering_mode", "bic", "lei", "address_from_listing"):
            assert hit.get(absent) is None


def test_the_creditor_reference_never_carries_a_name(mentions: list[tuple[dict, dict]]) -> None:
    for envelope, hit in mentions:
        transaction = f"{PMT_INF}/CdtTrfTxInf[{hit['transaction_number']}]"
        for reference in resolve(tree(envelope), f"{transaction}/RmtInf/Strd/CdtrRefInf/Ref"):
            assert str(reference.text).startswith("RF")


def test_the_remittance_element_follows_the_spec_weights(mentions: list[tuple[dict, dict]]) -> None:
    counts = Counter(hit["element"] for _, hit in mentions)
    total = sum(counts.values())

    assert counts["ustrd"] / total == pytest.approx(0.70, abs=0.08), counts
    assert counts["addtl_rmt_inf"] / total == pytest.approx(0.15, abs=0.06), counts
    assert (counts["invcr"] + counts["invcee"]) / total == pytest.approx(0.15, abs=0.06), counts


def test_the_summary_counts_remittance_mentions(mentions: list[tuple[dict, dict]]) -> None:
    envelope, _ = mentions[0]
    key = envelope["answer_key"]

    assert key["summary"]["by_placement"]["remittance"] == sum(h["placement"] == "remittance" for h in key["hits"])


def test_a_sentence_that_would_exceed_140_characters_is_redrawn(tmp_path: Path) -> None:
    long_name = "N" * 118  # fits a short template, not a long one
    bank = MINIMAL_BANK.replace('"TEST BANK"', f'"{long_name}"')
    assert long_name in bank
    write_catalogue(tmp_path, {"test-bank": bank})
    with TestClient(create_app(catalogue_root=tmp_path)) as client:
        envelopes = [generate(client, seed=f"long-{n}", transaction_count=100, hit_count=100) for n in range(2)]

    sentences = [
        str(resolve(tree(e), hit["xpath"])[0].text)
        for e in envelopes
        for hit in e["answer_key"]["hits"]
        if hit.get("element") in {"ustrd", "addtl_rmt_inf"}
    ]
    assert sentences
    assert all(long_name in s and len(s) <= 140 for s in sentences)
