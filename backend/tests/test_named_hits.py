"""`POST /api/v1/sample-files` with `hits[]` and allowlists: named Hits, rendering modes and controllers (spec 6.4,
6.6, 6.8, 11.3)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sample_files import resolve
from test_clean_banks import scratch_catalogue
from test_drawn_hits import PMT_INF, generate, tree

from pain_demo.app import create_app


def hits_of(client: TestClient, **settings: object) -> list[dict]:
    return generate(client, **settings)["answer_key"]["hits"]


def problem_errors(client: TestClient, settings: dict) -> list[dict]:
    response = client.post("/api/v1/sample-files", json=settings)
    assert response.status_code == 422, response.text
    assert response.json()["type"].endswith("validation_error")
    return response.json()["errors"]


def test_a_fully_pinned_named_hit_lands_where_asked(client: TestClient) -> None:
    envelope = generate(
        client,
        seed="pinned",
        transaction_count=5,
        hit_count=1,
        hits=[{"entity": "rosneft", "placement": "creditor", "name_variant": "alias", "transaction": 4}],
    )
    (hit,) = envelope["answer_key"]["hits"]

    assert (hit["entity"]["id"], hit["placement"], hit["transaction_number"]) == ("rosneft", "creditor", 4)
    assert (hit["name"]["variant"], hit["origin"]) == ("alias", "named")
    assert hit["xpath"] == f"{PMT_INF}/CdtTrfTxInf[4]/Cdtr/Nm"
    (element,) = resolve(tree(envelope), hit["xpath"])
    assert element.text == hit["name"]["rendered"]


def test_what_a_named_hit_leaves_out_is_drawn_and_it_counts_toward_hit_count(client: TestClient) -> None:
    hits = hits_of(client, seed="half-named", transaction_count=10, hit_count=3, hits=[{"entity": "vtb-bank"}])

    named = [hit for hit in hits if hit["origin"] == "named"]
    assert [hit["entity"]["id"] for hit in named] == ["vtb-bank"]
    assert len(hits) == 3
    assert sum(hit["origin"] == "drawn" for hit in hits) == 2


def test_two_named_hits_may_share_a_transaction_and_drawn_hits_keep_out_of_it(client: TestClient) -> None:
    hits = hits_of(
        client,
        seed="stacked",
        transaction_count=6,
        hit_count=6,
        hits=[
            {"entity": "rosneft", "placement": "creditor", "transaction": 2},
            {"entity": "igor-sechin", "placement": "ultimate_debtor", "transaction": 2},
            {"entity": "vtb-bank", "placement": "intermediary_agent_2", "transaction": 2},
            {"entity": "sberbank", "placement": "intermediary_agent_1", "transaction": 2},
        ],
    )

    in_two = [hit for hit in hits if hit.get("transaction_number") == 2]
    assert {hit["entity"]["id"] for hit in in_two} == {"rosneft", "igor-sechin", "vtb-bank", "sberbank"}
    drawn = [hit for hit in hits if hit["origin"] == "drawn"]
    assert len(drawn) == 2
    assert all(hit.get("transaction_number") != 2 for hit in drawn)


def test_allowlists_constrain_only_the_drawn_hits(client: TestClient) -> None:
    hits = hits_of(
        client,
        seed="allowlisted",
        transaction_count=20,
        hit_count=8,
        placements=["creditor_agent"],
        name_variants=["exact"],
        hits=[{"entity": "rosneft", "placement": "ultimate_debtor", "name_variant": "fuzzed"}],
    )

    drawn = [hit for hit in hits if hit["origin"] == "drawn"]
    assert len(drawn) == 7
    assert {(hit["placement"], hit["name"]["variant"]) for hit in drawn} == {("creditor_agent", "exact")}
    (named,) = [hit for hit in hits if hit["origin"] == "named"]
    assert (named["placement"], named["name"]["variant"]) == ("ultimate_debtor", "fuzzed")


@pytest.mark.parametrize(("version", "bic_element"), [("pain.001.001.03", "BIC"), ("pain.001.001.09", "BICFI")])
def test_bic_only_emits_the_bic_and_no_name(client: TestClient, version: str, bic_element: str) -> None:
    envelope = generate(
        client,
        seed="bic-only",
        message_version=version,
        hit_count=1,
        hits=[{"entity": "sberbank", "placement": "creditor_agent", "transaction": 1, "rendering_mode": "bic_only"}],
    )
    (hit,) = envelope["answer_key"]["hits"]
    document = tree(envelope)

    assert (hit["rendering_mode"], hit["name"]) == ("bic_only", None)
    assert hit["xpath"] == f"{PMT_INF}/CdtTrfTxInf[1]/CdtrAgt/FinInstnId/{bic_element}"
    (element,) = resolve(document, hit["xpath"])
    assert element.text == hit["bic"]["value"]
    assert resolve(document, f"{PMT_INF}/CdtTrfTxInf[1]/CdtrAgt/FinInstnId/Nm") == []
    assert [trigger["kind"] for trigger in hit["triggers"]] == ["bic"]


def test_a_gleif_sourced_bic_triggers_on_no_list(client: TestClient) -> None:
    (hit,) = hits_of(
        client,
        seed="gleif",
        hit_count=1,
        hits=[{"entity": "alfa-bank-belarus", "placement": "creditor_agent", "rendering_mode": "bic_only"}],
    )

    assert hit["bic"]["source"] == "gleif"
    assert hit["triggers"] == [{"kind": "bic", "value": hit["bic"]["value"], "listed_on": []}]


def test_name_only_emits_the_name_and_address_without_the_bic(client: TestClient) -> None:
    envelope = generate(
        client,
        seed="name-only",
        hit_count=1,
        hits=[{"entity": "sberbank", "placement": "debtor_agent", "rendering_mode": "name_only"}],
    )
    (hit,) = envelope["answer_key"]["hits"]
    document = tree(envelope)

    assert (hit["rendering_mode"], hit["bic"]) == ("name_only", None)
    assert resolve(document, hit["xpath"])[0].text == hit["name"]["rendered"]
    assert resolve(document, f"{PMT_INF}/DbtrAgt/FinInstnId/BIC") == []
    assert resolve(document, f"{PMT_INF}/DbtrAgt/FinInstnId/PstlAdr")
    assert "bic" not in {trigger["kind"] for trigger in hit["triggers"]}


def test_with_controller_places_the_controller_as_the_matching_ultimate_party(client: TestClient) -> None:
    hits = hits_of(
        client,
        seed="controlled",
        transaction_count=5,
        hit_count=2,
        hits=[{"entity": "evraz-plc", "placement": "creditor", "transaction": 3, "with_controller": True}],
    )

    creditor, controller = sorted(hits, key=lambda hit: hit["placement"])
    assert (creditor["entity"]["id"], creditor["placement"]) == ("evraz-plc", "creditor")
    assert controller["entity"]["id"] in {"roman-abramovich", "alexander-abramov"}
    assert controller["placement"] == "ultimate_creditor"
    assert creditor["transaction_number"] == controller["transaction_number"] == 3
    assert (creditor["paired_with"], controller["paired_with"]) == (controller["id"], creditor["id"])


def test_a_debtor_with_controller_brings_the_ultimate_debtor_into_a_transaction(client: TestClient) -> None:
    hits = hits_of(
        client,
        seed="debtor-pair",
        hit_count=2,
        hits=[{"entity": "rosneft", "placement": "debtor", "with_controller": True}],
    )

    debtor, ultimate = sorted(hits, key=lambda hit: hit["placement"])
    assert (debtor["scope"], debtor["entity"]["id"]) == ("file", "rosneft")
    assert (ultimate["placement"], ultimate["entity"]["id"]) == ("ultimate_debtor", "igor-sechin")
    assert ultimate["scope"] == "transaction"
    assert (debtor["paired_with"], ultimate["paired_with"]) == (ultimate["id"], debtor["id"])


@pytest.mark.parametrize(
    ("hits", "field", "entity"),
    [
        ([{"entity": "rosneft", "placement": "creditor_agent"}], "hits[0].placement", "rosneft"),
        ([{"entity": "syriatel", "name_variant": "transliteration"}], "hits[0].name_variant", "syriatel"),
        ([{"entity": "sberbank", "transaction": 11}], "hits[0].transaction", "sberbank"),
        ([{"entity": "sberbank", "placement": "debtor", "transaction": 1}], "hits[0].transaction", "sberbank"),
        (
            [{"entity": "rosneft", "placement": "debtor"}, {"entity": "alrosa", "placement": "debtor"}],
            "hits[1].placement",
            "alrosa",
        ),
        (
            [{"entity": "vtb-bank", "placement": "debtor_agent"}, {"entity": "t-bank", "placement": "debtor_agent"}],
            "hits[1].placement",
            "t-bank",
        ),
        ([{"entity": "rosneft", "rendering_mode": "name_only"}], "hits[0].rendering_mode", "rosneft"),
        (
            [{"entity": "sberbank", "placement": "creditor", "rendering_mode": "bic_only"}],
            "hits[0].rendering_mode",
            "sberbank",
        ),
        (
            [{"entity": "sberbank", "rendering_mode": "bic_only", "name_variant": "exact"}],
            "hits[0].name_variant",
            "sberbank",
        ),
        ([{"entity": "bank-mellat", "with_controller": True}], "hits[0].with_controller", "bank-mellat"),
        (
            [{"entity": "evraz-plc", "placement": "remittance", "with_controller": True}],
            "hits[0].with_controller",
            "evraz-plc",
        ),
        ([{"entity": "no-such-entity"}], "hits[0].entity", "no-such-entity"),
    ],
)
def test_impossible_named_hits_are_422s_naming_the_entity_and_field(
    client: TestClient, hits: list[dict], field: str, entity: str
) -> None:
    errors = problem_errors(client, {"transaction_count": 10, "hit_count": 2, "hits": hits})

    assert [error["field"] for error in errors] == [field]
    assert entity in errors[0]["message"]


def test_more_named_hits_than_hit_count_is_a_422(client: TestClient) -> None:
    errors = problem_errors(client, {"hit_count": 1, "hits": [{"entity": "evraz-plc", "with_controller": True}]})

    assert [error["field"] for error in errors] == ["hits"]


def test_allowlists_that_leave_a_drawn_hit_nowhere_to_go_are_a_422(client: TestClient) -> None:
    errors = problem_errors(client, {"hit_count": 2, "placements": ["debtor"]})

    assert [error["field"] for error in errors] == ["hit_count"]


def test_bic_only_on_a_bank_without_a_catalogue_bic_is_a_422(tmp_path: Path) -> None:
    scratch_catalogue(tmp_path, {"plain-bank": "PLAINVIEW TEST BANK"}, {})
    with TestClient(create_app(catalogue_root=tmp_path)) as client:
        hits = [{"entity": "plain-bank", "rendering_mode": "bic_only"}]
        errors = problem_errors(client, {"hit_count": 1, "hits": hits})

    assert [error["field"] for error in errors] == ["hits[0].rendering_mode"]
    assert "plain-bank" in errors[0]["message"]


@pytest.mark.parametrize("seed", [f"distinct-{n}" for n in range(4)])
def test_drawn_hits_do_not_reuse_an_entity_a_named_hit_uses(client: TestClient, seed: str) -> None:
    hits = hits_of(
        client,
        seed=seed,
        transaction_count=40,
        hit_count=40,
        hits=[{"entity": "evraz-plc", "placement": "creditor", "with_controller": True}],
    )

    named = {hit["entity"]["id"] for hit in hits if hit["origin"] == "named"}
    drawn = [hit["entity"]["id"] for hit in hits if hit["origin"] == "drawn"]
    assert not named & set(drawn)
    assert len(set(drawn)) == len(drawn)
