"""`POST /api/v1/sample-files` with `hit_count`: drawn Hits on party and agent Placements (spec 6, 7, 11)."""

from collections import Counter

import pytest
from fastapi.testclient import TestClient
from lxml import etree
from sample_files import assert_valid_sample_file, resolve

from pain_demo.app import create_app
from pain_demo.catalogue import load_catalogue
from pain_demo.generation.clean_banks import load_clean_banks

CATALOGUE = load_catalogue()
CLEAN_BICS = {bank.bic for bank in load_clean_banks(CATALOGUE).banks}
PARTIES = {"debtor", "creditor", "ultimate_debtor", "ultimate_creditor"}
FIXED = {"created_at": "2026-11-12T09:30:00Z", "execution_date": "2026-11-13"}
PMT_INF = "/Document/CstmrCdtTrfInitn/PmtInf"


def generate(client: TestClient, **settings: object) -> dict:
    response = client.post("/api/v1/sample-files", json={**FIXED, **settings})
    assert response.status_code == 200, response.text
    envelope = response.json()
    assert_valid_sample_file(xml_of(envelope), envelope["answer_key"]["message_version"])
    return envelope


def xml_of(envelope: dict) -> bytes:
    return envelope["sample_file"]["xml"].encode("utf-8")


def tree(envelope: dict) -> etree._Element:
    return etree.fromstring(xml_of(envelope))


def beside(document: etree._Element, xpath: str, name: str) -> list[str]:
    """Text of `name` next to the element at `xpath`, e.g. the BIC beside an agent's `Nm`."""
    return [str(e.text) for e in resolve(document, xpath.rsplit("/", 1)[0] + "/" + name)]


@pytest.fixture(scope="module")
def full() -> dict:
    """Every transaction plus both file-level Placements: each Entity placed twice, two of them three times."""
    with TestClient(create_app()) as client:
        return generate(client, seed="full-house", transaction_count=100, hit_count=102)


def test_each_hit_names_a_listed_entity_at_its_xpath(client: TestClient) -> None:
    envelope = generate(client, seed="three-hits", transaction_count=10, hit_count=3)
    key = envelope["answer_key"]
    document = tree(envelope)

    assert key["file"]["hit_count"] == 3
    assert [hit["id"] for hit in key["hits"]] == ["h1", "h2", "h3"]
    for hit in key["hits"]:
        (element,) = resolve(document, hit["xpath"])
        assert element.text == hit["name"]["rendered"]
        entity = CATALOGUE.entities[hit["entity"]["id"]]
        assert hit["name"]["rendered"] in [name.value for name in entity.names]
        assert hit["entity"]["entity_type"] == entity.entity_type
        assert hit["entity"]["listings"] == [{"list": x.list, "entry_id": x.entry_id} for x in entity.listings]
        assert (hit["origin"], hit["paired_with"], hit["displaced"]) == ("drawn", None, None)


def test_file_level_hits_carry_no_transaction_coordinates(client: TestClient) -> None:
    key = generate(client, seed="wire", transaction_count=1, hit_count=3)["answer_key"]

    debtor, debtor_agent, tx_hit = key["hits"]
    assert list(debtor) == [
        "id",
        "scope",
        "xpath",
        "entity",
        "placement",
        "name",
        "bic",
        "lei",
        "address_from_listing",
        "triggers",
        "origin",
        "paired_with",
        "displaced",
    ]
    assert (debtor["scope"], debtor["xpath"]) == ("file", f"{PMT_INF}/Dbtr/Nm")
    assert (debtor_agent["xpath"], debtor_agent["rendering_mode"]) == (
        f"{PMT_INF}/DbtrAgt/FinInstnId/Nm",
        "name_and_bic",
    )
    assert list(tx_hit)[:4] == ["id", "scope", "transaction_number", "end_to_end_id"]
    assert (tx_hit["scope"], tx_hit["transaction_number"]) == ("transaction", 1)
    assert tx_hit["end_to_end_id"] == key["transactions"][0]["end_to_end_id"]
    assert key["transactions"][0]["hit_ids"] == ["h1", "h2", "h3"]


@pytest.mark.parametrize("seed", [f"forced-{n}" for n in range(12)])
def test_two_hits_over_the_transaction_count_take_the_debtor_and_a_bank_as_debtor_agent(
    client: TestClient, seed: str
) -> None:
    key = generate(client, seed=seed, transaction_count=1, hit_count=3)["answer_key"]

    file_hits = {hit["placement"]: hit for hit in key["hits"] if hit["scope"] == "file"}
    assert set(file_hits) == {"debtor", "debtor_agent"}
    assert file_hits["debtor_agent"]["entity"]["entity_type"] == "bank"
    assert len({hit["entity"]["id"] for hit in key["hits"]}) == 3


@pytest.mark.parametrize("seed", [f"one-over-{n}" for n in range(6)])
def test_one_hit_over_the_transaction_count_goes_to_the_file_level(client: TestClient, seed: str) -> None:
    key = generate(client, seed=seed, transaction_count=2, hit_count=3)["answer_key"]

    assert sum(hit["scope"] == "file" for hit in key["hits"]) >= 1
    assert all(t["hit_ids"] for t in key["transactions"])


def test_hits_are_eligible_one_per_transaction_and_distinct_until_the_catalogue_is_exhausted(full: dict) -> None:
    hits = full["answer_key"]["hits"]

    assert len(hits) == full["answer_key"]["file"]["hit_count"] == 102
    assert sorted(hit["placement"] for hit in hits if hit["scope"] == "file") == ["debtor", "debtor_agent"]
    assert sorted(hit["transaction_number"] for hit in hits if hit["scope"] == "transaction") == list(range(1, 101))
    assert len(CATALOGUE.entities) == 50
    assert set(Counter(hit["entity"]["id"] for hit in hits).values()) == {2, 3}
    for hit in hits:
        assert hit["entity"]["entity_type"] == "bank" or hit["placement"] in PARTIES, hit


def test_hits_are_ordered_file_level_first_then_by_transaction(full: dict) -> None:
    hits = full["answer_key"]["hits"]

    order = [(hit["scope"] != "file", hit.get("transaction_number", 0), hit["xpath"]) for hit in hits]
    assert order == sorted(order)
    assert [hit["id"] for hit in hits] == [f"h{n}" for n in range(1, 103)]
    by_number = {hit["transaction_number"]: hit["id"] for hit in hits if hit["scope"] == "transaction"}
    file_ids = [hit["id"] for hit in hits if hit["scope"] == "file"]
    for transaction in full["answer_key"]["transactions"]:
        assert transaction["hit_ids"] == [*file_ids, by_number[transaction["number"]]]


def test_the_summary_counts_hits_by_placement_variant_type_and_list(full: dict) -> None:
    key = full["answer_key"]
    hits = key["hits"]

    assert key["summary"]["by_placement"] == dict(sorted(Counter(h["placement"] for h in hits).items()))
    assert key["summary"]["by_name_variant"] == dict(sorted(Counter(h["name"]["variant"] for h in hits).items()))
    assert key["summary"]["by_entity_type"] == dict(sorted(Counter(h["entity"]["entity_type"] for h in hits).items()))
    on_list = Counter(
        listing["list"] for h in hits for listing in {x["list"]: x for x in h["entity"]["listings"]}.values()
    )
    assert key["summary"]["by_list"] == dict(sorted(on_list.items()))
    assert sum(key["summary"]["by_placement"].values()) == 102
    assert key["summary"]["by_exposure_country"] == {}


def test_an_entity_in_a_higher_intermediary_slot_gets_clean_banks_below_it(full: dict) -> None:
    document = tree(full)
    slots = Counter()
    for hit in full["answer_key"]["hits"]:
        if hit["placement"].startswith("intermediary_agent_"):
            slot = int(hit["placement"][-1])
            slots[slot] += 1
            transaction = f"{PMT_INF}/CdtTrfTxInf[{hit['transaction_number']}]"
            for lower in range(1, slot):
                assert set(beside(document, f"{transaction}/IntrmyAgt{lower}/FinInstnId/Nm", "BIC")) <= CLEAN_BICS
                assert len(beside(document, f"{transaction}/IntrmyAgt{lower}/FinInstnId/Nm", "BIC")) == 1
            assert resolve(document, f"{transaction}/IntrmyAgt{slot + 1}") == []
    assert slots[1] > 0


def test_names_are_listed_verbatim_with_their_source_and_variant(full: dict) -> None:
    for hit in full["answer_key"]["hits"]:
        name = hit["name"]
        entity = CATALOGUE.entities[hit["entity"]["id"]]
        listed = [
            {"value": n.value, "type": n.source_type, "script": n.script, "listing": n.listing.model_dump()}
            for n in entity.names
        ]
        assert name["source"] in listed
        assert name["rendered"] == name["source"]["value"]
        source = entity.names[listed.index(name["source"])]
        expected = {
            "exact": source.source_type == "primary" and source.script == "latin",
            "alias": source.source_type != "primary" and source.script == "latin",
            "native_script": source.script != "latin",
        }
        assert expected[name["variant"]], (hit["entity"]["id"], name)
