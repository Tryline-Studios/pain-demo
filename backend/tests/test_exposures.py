"""Exposures (spec 8, 11.5): clean transactions whose creditor side sits in a sanctioned or high-risk country."""

import re
from collections import Counter

import pytest
from fastapi.testclient import TestClient
from lxml import etree
from sample_files import resolve
from schwifty import IBAN
from test_drawn_hits import CATALOGUE, CLEAN_BICS, PMT_INF, generate, tree

from pain_demo.app import create_app
from pain_demo.generation.screening import NameScreen
from pain_demo.identifiers import bic_country

EXPOSURE_CURRENCIES = {"RU": "RUB", "BY": "BYN", "IR": "IRR", "KP": "KPW", "SY": "SYP", "VE": "VES"}
CITIES = {
    "RU": {"Moscow", "St Petersburg", "Novosibirsk", "Yekaterinburg", "Kazan"},
    "BY": {"Minsk", "Gomel", "Brest", "Grodno", "Vitebsk"},
    "IR": {"Tehran", "Mashhad", "Isfahan", "Tabriz", "Shiraz"},
    "KP": {"Pyongyang", "Hamhung", "Chongjin", "Nampo", "Wonsan"},
    "SY": {"Damascus", "Aleppo", "Homs", "Latakia", "Hama"},
    "VE": {"Caracas", "Maracaibo", "Valencia", "Barquisimeto", "Maracay"},
}
RUSSIAN_NAME = re.compile(r"(vich|vna|ichna)\b|^(OOO|ZAO|OAO|NPO|PAO|AO|IP|RAO)\b")
"""A romanised Faker ru_RU person (a patronymic) or company (a legal-form prefix)."""


def test_options_publish_the_exposure_countries_with_their_currencies(client: TestClient) -> None:
    options = client.get("/api/v1/options").json()

    assert options["exposure_countries"] == [{"country": c, "currency": v} for c, v in EXPOSURE_CURRENCIES.items()]
    assert options["defaults"]["exposure_countries"] == list(EXPOSURE_CURRENCIES)


@pytest.mark.parametrize(
    ("settings", "field", "code"),
    [
        ({"exposure_countries": ["RU", "GB"], "exposure_count": 1}, "exposure_countries[1]", "literal_error"),
        ({"exposure_countries": []}, "exposure_countries", "too_short"),
        ({"exposure_count": -1}, "exposure_count", "greater_than_equal"),
        ({"transaction_count": 3, "exposure_count": 4}, "exposure_count", "value_error"),
        # Two Hits beyond the file-level pair need two transactions, which leaves one for Exposures.
        ({"transaction_count": 3, "hit_count": 4, "exposure_count": 2}, "exposure_count", "value_error"),
    ],
)
def test_invalid_exposure_settings_are_422_problems_naming_the_field(
    client: TestClient, settings: dict, field: str, code: str
) -> None:
    response = client.post("/api/v1/sample-files", json=settings)

    assert response.status_code == 422
    assert [(e["field"], e["code"]) for e in response.json()["errors"]] == [(field, code)]


def transaction(document: etree._Element, number: int) -> etree._Element:
    (element,) = resolve(document, f"{PMT_INF}/CdtTrfTxInf[{number}]")
    return element


def text(element: etree._Element, path: str) -> list[str]:
    return [str(e.text) for e in resolve(element, path)]


@pytest.fixture(scope="module")
def exposed() -> dict:
    """Every country several times over, beside Hits and a `currencies` list the Exposures ignore."""
    with TestClient(create_app()) as client:
        return generate(
            client,
            seed="exposed",
            transaction_count=100,
            hit_count=20,
            exposure_count=60,
            currencies=["EUR"],
            message_version="pain.001.001.09",
        )


def test_exposures_are_listed_apart_from_hits_on_transactions_no_hit_touches(exposed: dict) -> None:
    key = exposed["answer_key"]
    exposures = key["exposures"]
    hit_transactions = {hit.get("transaction_number") for hit in key["hits"]}
    file_level = [hit["id"] for hit in key["hits"] if hit["scope"] == "file"]

    assert len(exposures) == 60
    assert key["file"]["hit_count"] == len(key["hits"]) == 20
    numbers = [e["transaction_number"] for e in exposures]
    assert numbers == sorted(set(numbers))
    assert not set(numbers) & hit_transactions
    for exposure in exposures:
        row = key["transactions"][exposure["transaction_number"] - 1]
        assert row["hit_ids"] == file_level  # a sanctioned Debtor or Debtor Agent touches every transaction
        assert exposure["end_to_end_id"] == row["end_to_end_id"]
        assert exposure["elements"] == ["creditor_address", "agent_bic", "account"]
    countries = Counter(e["country"] for e in exposures)
    assert set(countries) == set(EXPOSURE_CURRENCIES)
    assert key["summary"]["by_exposure_country"] == dict(sorted(countries.items()))


def test_an_exposed_creditor_side_sits_wholly_in_its_country(exposed: dict) -> None:
    document = tree(exposed)
    for exposure in exposed["answer_key"]["exposures"]:
        country = exposure["country"]
        tx = transaction(document, exposure["transaction_number"])

        assert exposure["currency"] == EXPOSURE_CURRENCIES[country]
        assert resolve(tx, "Amt/InstdAmt")[0].get("Ccy") == EXPOSURE_CURRENCIES[country]
        assert text(tx, "Cdtr/PstlAdr/Ctry") == [country]
        (town,) = text(tx, "Cdtr/PstlAdr/TwnNm")
        assert town in CITIES[country]
        (bic,) = text(tx, "CdtrAgt/FinInstnId/BICFI")
        assert (bic_country(bic), len(bic), bic[7]) == (country, 8, "0")  # `0` is the ISO test-BIC marker
        assert text(tx, "CdtrAgt/FinInstnId/Nm")
        (account,) = resolve(tx, "CdtrAcct/Id/*")
        if country in {"BY", "IR"}:
            iban = IBAN(str(account.text))
            assert iban.country_code == country
            if country == "BY":
                assert iban.bank_code == bic[:4]
        else:
            (number,) = text(account, "Id")
            assert number.isdigit()
            assert len(number) == (20 if country == "RU" else 16)


def test_exposed_names_are_latin_and_screened(exposed: dict) -> None:
    document = tree(exposed)
    screen = NameScreen(CATALOGUE)
    for exposure in exposed["answer_key"]["exposures"]:
        tx = transaction(document, exposure["transaction_number"])
        for value in (*text(tx, "Cdtr/Nm"), *text(tx, "CdtrAgt/FinInstnId/Nm")):
            assert not re.search(r"[Ѐ-ӿ«»]", value), value
            assert not screen.matches(value), value


def test_ru_and_by_names_are_romanised_faker_ru_and_the_rest_from_the_request_locales(client: TestClient) -> None:
    envelope = generate(client, seed="locales", transaction_count=40, exposure_count=40, countries=["DE"])
    document = tree(envelope)
    seen: Counter[tuple[bool, bool]] = Counter()
    for exposure in envelope["answer_key"]["exposures"]:
        (name,) = text(transaction(document, exposure["transaction_number"]), "Cdtr/Nm")
        seen[exposure["country"] in {"RU", "BY"}, bool(RUSSIAN_NAME.search(name))] += 1

    assert seen[True, True] >= 3 * seen[True, False]  # Faker's few big-company names have no legal form
    assert seen[False, False] > 0  # a German name at a Tehran or Caracas address
    assert seen[False, True] == 0


def test_an_exposure_never_moves_a_hit(client: TestClient) -> None:
    settings = {"seed": "steady", "transaction_count": 20, "hit_count": 5}
    plain = generate(client, **settings)["answer_key"]["hits"]

    assert generate(client, **settings, exposure_count=4)["answer_key"]["hits"] == plain


def test_a_sanctioned_creditor_in_an_exposure_country_banks_with_a_local_test_bic(client: TestClient) -> None:
    """Spec open point 10: its account and its agent agree."""
    envelope = generate(
        client, seed="full-house", transaction_count=100, hit_count=102, message_version="pain.001.001.09"
    )
    document = tree(envelope)
    local = 0
    for hit in envelope["answer_key"]["hits"]:
        if hit["placement"] != "creditor":
            continue
        tx = transaction(document, hit["transaction_number"])
        (bic,) = text(tx, "CdtrAgt/FinInstnId/BICFI")
        (account,) = resolve(tx, "CdtrAcct/Id/*")
        iban_country = IBAN(str(account.text)).country_code if etree.QName(account).localname == "IBAN" else None
        if bic_country(bic) in EXPOSURE_CURRENCIES:
            assert bic[7] == "0"
            assert iban_country in {None, bic_country(bic)}
            local += 1
        else:
            assert bic in CLEAN_BICS
            assert iban_country not in EXPOSURE_CURRENCIES
    assert local > 0


def test_a_sanctioned_debtor_in_an_exposure_country_banks_with_a_local_test_bic(client: TestClient) -> None:
    local = 0
    for n in range(40):
        envelope = generate(client, seed=f"debtor-{n}", transaction_count=1, hit_count=2)
        placements = {hit["placement"] for hit in envelope["answer_key"]["hits"]}
        if "debtor" not in placements or "debtor_agent" in placements:
            continue
        document = tree(envelope)
        (bic,) = text(document, f"{PMT_INF}/DbtrAgt/FinInstnId/BIC")
        (account,) = resolve(document, f"{PMT_INF}/DbtrAcct/Id/*")
        if bic_country(bic) in EXPOSURE_CURRENCIES:
            assert bic[7] == "0"
            if etree.QName(account).localname == "IBAN":
                assert IBAN(str(account.text)).country_code == bic_country(bic)
            local += 1
        else:
            assert bic in CLEAN_BICS
    assert local > 0


@pytest.mark.parametrize(
    ("hits", "room"),
    [
        ([{"entity": "sberbank", "placement": "creditor_agent"}, {"entity": "rosneft", "placement": "creditor"}], 1),
        # The controller's Ultimate Debtor takes a transaction beside the file-level Debtor.
        ([{"entity": "evraz-plc", "placement": "debtor", "with_controller": True}], 2),
    ],
)
def test_exposures_count_the_transactions_named_hits_take(client: TestClient, hits: list[dict], room: int) -> None:
    settings = {"transaction_count": 3, "hit_count": 2, "hits": hits}
    response = client.post("/api/v1/sample-files", json={**settings, "exposure_count": room + 1})

    assert response.status_code == 422, response.text
    assert [e["field"] for e in response.json()["errors"]] == ["exposure_count"]

    key = generate(client, **settings, exposure_count=room)["answer_key"]
    hit_numbers = {hit.get("transaction_number") for hit in key["hits"]}
    assert len(key["exposures"]) == room
    assert not hit_numbers & {e["transaction_number"] for e in key["exposures"]}


def test_a_422_for_drawn_hits_says_when_exposures_took_their_room(client: TestClient) -> None:
    settings = {"transaction_count": 3, "hit_count": 3, "placements": ["creditor"]}
    generate(client, **settings)

    response = client.post("/api/v1/sample-files", json={**settings, "exposure_count": 1})

    assert response.status_code == 422, response.text
    (error,) = response.json()["errors"]
    assert error["field"] == "hit_count"
    assert "exposure_count" in error["message"]
