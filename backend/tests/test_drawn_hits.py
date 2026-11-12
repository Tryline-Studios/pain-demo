"""`POST /api/v1/sample-files` with `hit_count`: drawn Hits on party and agent Placements (spec 6, 7, 11)."""

import json
from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from lxml import etree
from sample_files import assert_valid_sample_file, resolve
from schwifty import IBAN
from test_catalogue import MINIMAL_BANK, write_catalogue
from test_clean_banks import scratch_catalogue

from pain_demo.app import create_app
from pain_demo.catalogue import load_catalogue
from pain_demo.catalogue.capabilities import supported_name_variants
from pain_demo.catalogue.schema import Bank
from pain_demo.catalogue.transliteration import transliterate
from pain_demo.generation.clean_banks import IBAN_COUNTRIES, load_clean_banks
from pain_demo.identifiers import bic_country
from pain_demo.settings import Settings

CATALOGUE = load_catalogue()
CLEAN_BICS = {bank.bic for bank in load_clean_banks(CATALOGUE).banks}
PARTIES = {"debtor", "creditor", "ultimate_debtor", "ultimate_creditor"}
NOT_AGENTS = {*PARTIES, "remittance"}
FIXED = {"created_at": "2026-11-12T09:30:00Z", "execution_date": "2026-11-13"}
PMT_INF = "/Document/CstmrCdtTrfInitn/PmtInf"
VERBATIM = {"exact", "alias", "native_script"}


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
        return generate(
            client, seed="full-house", transaction_count=100, hit_count=102, message_version="pain.001.001.09"
        )


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
        assert hit["name"]["source"]["value"] in [name.value for name in entity.names]
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
        assert hit["entity"]["entity_type"] == "bank" or hit["placement"] in NOT_AGENTS, hit


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
                assert set(beside(document, f"{transaction}/IntrmyAgt{lower}/FinInstnId/Nm", "BICFI")) <= CLEAN_BICS
                assert len(beside(document, f"{transaction}/IntrmyAgt{lower}/FinInstnId/Nm", "BICFI")) == 1
            assert resolve(document, f"{transaction}/IntrmyAgt{slot + 1}") == []
    assert slots[1] > 0


def test_verbatim_names_are_listed_with_their_source_and_variant(full: dict) -> None:
    verbatim = [hit for hit in full["answer_key"]["hits"] if hit["name"]["variant"] in VERBATIM]
    assert {hit["name"]["variant"] for hit in verbatim} == VERBATIM
    for hit in verbatim:
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
        assert not {"scheme", "base", "operations"} & set(name)


def test_a_transliteration_records_its_scheme_and_is_on_no_list(full: dict) -> None:
    hits = [hit for hit in full["answer_key"]["hits"] if hit["name"]["variant"] == "transliteration"]
    assert hits
    for hit in hits:
        name = hit["name"]
        entity = CATALOGUE.entities[hit["entity"]["id"]]
        assert name["source"]["script"] == "cyrillic"
        assert name["source"]["value"] in [n.value for n in entity.names]
        assert name["rendered"] == transliterate(name["source"]["value"], name["scheme"])
        assert name["rendered"].casefold() not in {n.value.casefold() for n in entity.names}
        assert hit["triggers"][0] == {"kind": "name", "value": name["rendered"], "listed_on": []}
        assert not {"base", "operations"} & set(name)


def test_a_fuzz_records_its_listed_latin_base_and_its_operations_in_order(full: dict) -> None:
    hits = [hit for hit in full["answer_key"]["hits"] if hit["name"]["variant"] == "fuzzed"]
    assert hits
    for hit in hits:
        name = hit["name"]
        entity = CATALOGUE.entities[hit["entity"]["id"]]
        assert name["base"] == name["source"]["value"]
        assert name["source"]["script"] == "latin"
        assert name["base"] in [n.value for n in entity.names]
        assert 1 <= len(name["operations"]) <= 2
        assert name["rendered"] != name["base"]
        assert "scheme" not in name


ACCOUNT_OF = {"debtor": "DbtrAcct", "debtor_agent": "DbtrAcct", "creditor": "CdtrAcct", "creditor_agent": "CdtrAcct"}


def account(document: etree._Element, hit: dict) -> tuple[str, str]:
    """`("iban", value)` or `("other", value)` of the account the Hit's party holds or its agent services."""
    number = hit.get("transaction_number")
    holder = f"{PMT_INF}/CdtTrfTxInf[{number}]" if number else PMT_INF
    (element,) = resolve(document, f"{holder}/{ACCOUNT_OF[hit['placement']]}/Id/*")
    kind = etree.QName(element).localname
    return ("iban", str(element.text)) if kind == "IBAN" else ("other", str(resolve(element, "Id")[0].text))


def assert_account_in(kind_and_value: tuple[str, str], country: str) -> None:
    kind, value = kind_and_value
    if country in {"BY", "IR", *IBAN_COUNTRIES}:
        assert kind == "iban", (country, value)
        assert IBAN(value).country_code == country
    else:
        assert kind == "other", (country, value)
        assert value.isdigit()
        if country == "RU":
            assert len(value) == 20


def test_a_sanctioned_party_carries_its_listed_address_and_banks_in_that_country(full: dict) -> None:
    document = tree(full)
    for hit in full["answer_key"]["hits"]:
        if hit["placement"] not in PARTIES:
            continue
        entity = CATALOGUE.entities[hit["entity"]["id"]]
        addresses = getattr(entity, "addresses", [])
        if not addresses:
            assert hit["address_from_listing"] is None
            assert resolve(document, hit["xpath"].replace("/Nm", "/PstlAdr")) == []
            continue
        lines = beside(document, hit["xpath"], "PstlAdr/AdrLine")
        (address, *_) = [
            a
            for a in addresses
            if a.lines == lines[: len(a.lines)] and a.listing.entry_id == hit["address_from_listing"]
        ]
        assert beside(document, hit["xpath"], "PstlAdr/Ctry") == [address.country]
        if hit["placement"] == "creditor":
            assert_account_in(account(document, hit), address.country)


def debtor_country(document: etree._Element, hit: dict) -> str | None:
    """Where a sanctioned Debtor banks (spec 6.9): its Listing address, else its first stated country."""
    if hit["address_from_listing"]:
        return beside(document, hit["xpath"], "PstlAdr/Ctry")[0]
    countries = CATALOGUE.entities[hit["entity"]["id"]].countries
    return countries[0] if countries else None


def test_a_sanctioned_debtor_keeps_its_account_at_home_beside_a_sanctioned_debtor_agent(client: TestClient) -> None:
    envelope = generate(client, seed="s7", transaction_count=2, hit_count=4, message_version="pain.001.001.09")
    document = tree(envelope)

    debtor, debtor_agent = [hit for hit in envelope["answer_key"]["hits"] if hit["scope"] == "file"]
    assert (debtor["entity"]["id"], debtor_country(document, debtor)) == ("irisl", "IR")
    assert_account_in(account(document, debtor), "IR")
    # An Iranian Bank is eligible, so the Debtor Agent is one and services the account.
    assert bic_country(debtor_agent["bic"]["value"]) == "IR"
    assert beside(document, debtor_agent["xpath"], "BICFI") == [debtor_agent["bic"]["value"]]


@pytest.mark.parametrize("seed", [f"both-file-level-{n}" for n in range(40)])
def test_a_sanctioned_debtors_account_is_always_in_its_listing_country(client: TestClient, seed: str) -> None:
    envelope = generate(client, seed=seed, transaction_count=1, hit_count=3, message_version="pain.001.001.09")
    document = tree(envelope)

    debtor, debtor_agent = [hit for hit in envelope["answer_key"]["hits"] if hit["scope"] == "file"]
    country = debtor_country(document, debtor)
    if country:
        assert_account_in(account(document, debtor), country)
    assert resolve(document, debtor_agent["xpath"])[0].text == debtor_agent["name"]["rendered"]
    if debtor_agent["bic"]:
        assert beside(document, debtor_agent["xpath"], "BICFI") == [debtor_agent["bic"]["value"]]


def test_a_sanctioned_bank_as_agent_carries_its_bic_lei_and_address_and_services_an_account_at_home(full: dict) -> None:
    document = tree(full)
    agents = [hit for hit in full["answer_key"]["hits"] if hit["placement"] not in NOT_AGENTS]
    assert {hit["placement"] for hit in agents} >= {"debtor_agent", "creditor_agent", "intermediary_agent_1"}
    # A sanctioned Debtor elsewhere keeps its own account (spec 6.9).
    (debtor,) = [hit for hit in full["answer_key"]["hits"] if hit["placement"] == "debtor"]
    homes = {"debtor_agent": debtor_country(document, debtor)}
    for hit in agents:
        bank = CATALOGUE.entities[hit["entity"]["id"]]
        assert isinstance(bank, Bank)
        (bic,) = [b for b in bank.bics if b.value == hit["bic"]["value"]]
        country = bic_country(bic.value)
        assert hit["rendering_mode"] == "name_and_bic"
        assert hit["bic"]["source"] == ("listing" if bic.listing else "gleif")
        assert beside(document, hit["xpath"], "BICFI") == [bic.value]
        assert hit["lei"] == (bank.lei.value if bank.lei else None)
        assert beside(document, hit["xpath"], "LEI") == ([bank.lei.value] if bank.lei else [])
        if any(a.country == country for a in bank.addresses):
            assert beside(document, hit["xpath"], "PstlAdr/Ctry") == [country]
        if hit["placement"] in ACCOUNT_OF and country == homes.get(hit["placement"], country):
            assert_account_in(account(document, hit), country)
    assert {hit["entity"]["id"][:9] for hit in agents if hit["placement"] in ACCOUNT_OF} & {"bank-mell", "bank-dabr"}


def test_triggers_say_which_lists_carry_the_name_bic_and_lei(full: dict) -> None:
    for hit in full["answer_key"]["hits"]:
        entity = CATALOGUE.entities[hit["entity"]["id"]]
        rendered = hit["name"]["rendered"].casefold()
        expected = [
            {
                "kind": "name",
                "value": hit["name"]["rendered"],
                "listed_on": sorted({n.listing.list for n in entity.names if n.value.casefold() == rendered}),
            }
        ]
        if hit["bic"]:
            assert isinstance(entity, Bank)
            (bic,) = [b for b in entity.bics if b.value == hit["bic"]["value"]]
            expected.append({"kind": "bic", "value": bic.value, "listed_on": [bic.listing.list] if bic.listing else []})
        if hit["lei"]:
            expected.append({"kind": "lei", "value": hit["lei"], "listed_on": []})
        assert hit["triggers"] == expected


def test_an_lei_is_not_claimed_where_the_message_version_cannot_carry_it(client: TestClient) -> None:
    envelope = generate(client, seed="forced-0", transaction_count=1, hit_count=3, message_version="pain.001.001.03")
    key = envelope["answer_key"]

    (agent,) = [hit for hit in key["hits"] if hit["placement"] == "debtor_agent"]
    assert agent["lei"] is None
    assert [t["kind"] for t in agent["triggers"]] == ["name", "bic"]
    assert beside(tree(envelope), agent["xpath"], "BIC") == [agent["bic"]["value"]]
    assert key["warnings"] == []


def test_a_bank_without_a_catalogue_bic_is_placed_by_name_only(tmp_path: Path) -> None:
    scratch_catalogue(tmp_path, {"plain-bank": "PLAINVIEW TEST BANK"}, {})
    with TestClient(create_app(catalogue_root=tmp_path)) as client:
        envelope = generate(client, seed="no-bic", transaction_count=5, hit_count=7, message_version="pain.001.001.13")

    document = tree(envelope)
    agents = [hit for hit in envelope["answer_key"]["hits"] if hit["placement"] not in NOT_AGENTS]
    assert agents
    for hit in agents:
        assert (hit["rendering_mode"], hit["bic"]) == ("name_only", None)
        assert [t["kind"] for t in hit["triggers"]] == ["name"]
        assert resolve(document, hit["xpath"])[0].text == hit["name"]["rendered"]
        assert hit["name"]["source"]["value"] == "PLAINVIEW TEST BANK"
        assert beside(document, hit["xpath"], "BICFI") == []


def primary_name(value: str, listing: str) -> str:
    return f"""
[[names]]
value = "{value}"
source_type = "primary"
script = "latin"
script_source = "stated"
listing = {listing}
"""


def test_an_exact_name_picks_a_listing_first_then_one_of_its_primary_names(tmp_path: Path) -> None:
    ofac, uk = '{ list = "ofac_sdn", entry_id = "1" }', '{ list = "uk", entry_id = "RUS0001" }'
    bank = (
        MINIMAL_BANK
        + """
[[listings]]
list = "uk"
entry_id = "RUS0001"
programmes = ["The Russia (Sanctions) (EU Exit) Regulations 2019"]
designation_date = 2022-03-10
verified = { snapshot_date = 2026-09-11, source_file = "UK-Sanctions-List.xml" }
"""
        + primary_name("TEST BANK TWO", ofac)
        + primary_name("TEST BANK THREE", ofac)
        + primary_name("Test Bank PLC", uk)
    )
    write_catalogue(tmp_path, {"test-bank": bank})
    with TestClient(create_app(catalogue_root=tmp_path)) as client:
        hits = [
            hit
            for n in range(3)
            for hit in generate(client, seed=f"exact-{n}", transaction_count=100, hit_count=100)["answer_key"]["hits"]
        ]

    # Three OFAC primaries against one UK primary: the UK name takes half the draws, not a quarter (spec 7.1).
    assert {hit["name"]["variant"] for hit in hits} == {"exact", "fuzzed"}
    exact = [hit for hit in hits if hit["name"]["variant"] == "exact"]
    uk_share = sum(hit["name"]["source"]["listing"]["list"] == "uk" for hit in exact) / len(exact)
    assert uk_share == pytest.approx(0.5, abs=0.08)


def test_names_over_140_characters_are_never_chosen(tmp_path: Path) -> None:
    long_name = "LONG" * 35 + "X"
    bank = MINIMAL_BANK + "".join(
        f"""
[[names]]
value = "{long_name}"
source_type = "{source_type}"
script = "latin"
script_source = "stated"
listing = {{ list = "ofac_sdn", entry_id = "1" }}
"""
        for source_type in ("primary", "aka")
    )
    write_catalogue(tmp_path, {"test-bank": bank})
    with TestClient(create_app(catalogue_root=tmp_path)) as client:
        hits = generate(client, seed="long", transaction_count=20, hit_count=22)["answer_key"]["hits"]

    assert len(long_name) == 141
    assert {hit["name"]["source"]["value"] for hit in hits} == {"TEST BANK"}
    assert {hit["name"]["variant"] for hit in hits} == {"exact", "fuzzed"}


def test_placements_and_name_variants_follow_the_spec_weights(client: TestClient) -> None:
    hits = [
        hit
        for n in range(8)
        for hit in generate(client, seed=f"weights-{n}", transaction_count=100, hit_count=100)["answer_key"]["hits"]
    ]

    def shares(selected: list[dict], field: str) -> dict[str, float]:
        counts = Counter(field_of(hit, field) for hit in selected)
        return {key: count / len(selected) for key, count in counts.items()}

    def field_of(hit: dict, field: str) -> str:
        return hit["name"]["variant"] if field == "variant" else hit[field]

    # Debtor and Debtor Agent fill once per file and are redrawn after, so compare transaction-level shares only:
    # parties 35/25/15/15 over 90; Banks 40, 30 and 5 over 40 + 30 + 5 + 10 * 65/75 for their transaction-level party
    # roles.
    transaction_level = [h for h in hits if h["scope"] == "transaction"]
    parties = shares([h for h in transaction_level if h["entity"]["entity_type"] != "bank"], "placement")
    expected_parties = {
        "creditor": 35 / 90,
        "remittance": 25 / 90,
        "ultimate_creditor": 15 / 90,
        "ultimate_debtor": 15 / 90,
    }
    for placement, share in expected_parties.items():
        assert parties[placement] == pytest.approx(share, abs=0.07), parties
    banks = shares([h for h in transaction_level if h["entity"]["entity_type"] == "bank"], "placement")
    bank_total = 40 + 30 + 5 + 10 * 65 / 75
    assert banks["creditor_agent"] == pytest.approx(40 / bank_total, abs=0.07), banks
    assert banks["remittance"] == pytest.approx(5 / bank_total, abs=0.04), banks
    intermediaries = sum(share for placement, share in banks.items() if placement.startswith("intermediary"))
    assert intermediaries == pytest.approx(30 / bank_total, abs=0.07), banks
    assert banks["intermediary_agent_1"] > banks["intermediary_agent_2"] > banks["intermediary_agent_3"] > 0
    # Over the Entities that support all five: exact 40, alias 25, fuzzed 20, transliteration 10, native script 5.
    all_five = [h for h in hits if len(supported_name_variants(CATALOGUE.entities[h["entity"]["id"]])) == 5]
    every_variant = shares(all_five, "variant")
    expected = {"exact": 0.4, "alias": 0.25, "fuzzed": 0.2, "transliteration": 0.1, "native_script": 0.05}
    assert every_variant == pytest.approx(expected, abs=0.05), every_variant
    # Evraz NTMK has no non-Latin name, so it draws from exact, alias and fuzzed only (too few Hits to check shares).
    ntmk = shares([h for h in hits if h["entity"]["id"] == "evraz-ntmk"], "variant")
    assert set(ntmk) == {"exact", "alias", "fuzzed"}


def test_a_hit_leaves_every_other_transaction_untouched(client: TestClient) -> None:
    settings = {"seed": "innocent", "transaction_count": 20}
    clean = tree(generate(client, **settings))
    envelope = generate(client, **settings, hit_count=5)
    with_hits = tree(envelope)

    def transaction(document: etree._Element, number: int) -> bytes:
        return etree.tostring(resolve(document, f"{PMT_INF}/CdtTrfTxInf[{number}]")[0])

    hit = {h["transaction_number"] for h in envelope["answer_key"]["hits"] if h["scope"] == "transaction"}
    innocent = [number for number in range(1, 21) if number not in hit]
    assert len(innocent) >= 15
    for number in innocent:
        assert transaction(with_hits, number) == transaction(clean, number)


def test_generation_logs_the_hit_count(capsys: pytest.CaptureFixture[str]) -> None:
    with TestClient(create_app(Settings(log_format="json", log_level="INFO"))) as client:
        generate(client, seed="logged-hits", transaction_count=4, hit_count=2)

    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    (event,) = [e for e in events if e["event"] == "request"]
    assert (event["hit_count"], event["named_hit_count"]) == (2, 0)


def test_replaying_a_request_with_hits_reproduces_the_file_and_answer_key(client: TestClient) -> None:
    first = generate(client, transaction_count=12, hit_count=14, message_version="pain.001.001.11")

    assert generate(client, **first["answer_key"]["request"]) == first
