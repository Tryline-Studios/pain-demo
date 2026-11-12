"""`POST /api/v1/sample-files` with `payment` and `transactions[]`: Supplied Data merging (spec 5, 10.4, 11.3)."""

import pytest
from fastapi.testclient import TestClient
from lxml import etree
from sample_files import assert_valid_sample_file, resolve

FIXED = {"created_at": "2026-11-12T09:30:00Z", "execution_date": "2026-11-13"}
PMT_INF = "/Document/CstmrCdtTrfInitn/PmtInf"


def post(client: TestClient, **request: object) -> dict:
    response = client.post("/api/v1/sample-files", json={**FIXED, **request})
    assert response.status_code == 200, response.text
    envelope = response.json()
    assert_valid_sample_file(xml_of(envelope), envelope["answer_key"]["message_version"])
    return envelope


def xml_of(envelope: dict) -> bytes:
    return envelope["sample_file"]["xml"].encode("utf-8")


def tree(envelope: dict) -> etree._Element:
    return etree.fromstring(xml_of(envelope))


def text(document: etree._Element, xpath: str) -> list[str]:
    return [str(element.text) for element in resolve(document, xpath)]


def test_supplying_one_field_leaves_every_other_generated_value_unchanged(client: TestClient) -> None:
    generated = tree(post(client, seed="merge", transaction_count=10))
    supplied = tree(post(client, seed="merge", transaction_count=10, transactions=[{}, {"creditor": {"name": "Acme"}}]))

    (name,) = resolve(generated, f"{PMT_INF}/CdtTrfTxInf[2]/Cdtr/Nm")
    assert name.text != "Acme"
    name.text = "Acme"
    assert etree.tostring(supplied) == etree.tostring(generated)


def problems(client: TestClient, **request: object) -> list[dict]:
    response = client.post("/api/v1/sample-files", json={**FIXED, **request})
    assert response.status_code == 422, response.text
    return response.json()["errors"]


def test_null_leaves_an_optional_element_out(client: TestClient) -> None:
    row = {
        "ultimate_creditor": None,
        "ultimate_debtor": None,
        "intermediary_agents": None,
        "creditor": {"address": None},
        "remittance": {"unstructured": None, "structured": None},
    }
    document = tree(post(client, seed="nulls", transactions=[row] * 20))

    for element in ("UltmtCdtr", "UltmtDbtr", "IntrmyAgt1", "Cdtr/PstlAdr", "RmtInf"):
        assert resolve(document, f"{PMT_INF}/CdtTrfTxInf/{element}") == [], element
    assert len(resolve(document, f"{PMT_INF}/CdtTrfTxInf/Cdtr/Nm")) == 20


@pytest.mark.parametrize(
    ("request_part", "field"),
    [
        ({"transactions": [{"creditor": {"name": None}}]}, "transactions[0].creditor.name"),
        ({"transactions": [{"amount": None}]}, "transactions[0].amount"),
        ({"transactions": [{"creditor": None}]}, "transactions[0].creditor"),
        ({"payment": {"debtor_agent": None}}, "payment.debtor_agent"),
    ],
)
def test_null_on_a_required_element_is_a_422(client: TestClient, request_part: dict, field: str) -> None:
    assert [error["field"] for error in problems(client, **request_part)] == [field]


def test_the_transaction_count_defaults_to_the_rows_and_pads_with_generated_ones(client: TestClient) -> None:
    rows = [{"amount": "12.34"}, {}, {"amount": "56.78"}]
    three = post(client, seed="rows", transactions=rows)
    assert three["answer_key"]["file"]["transaction_count"] == 3
    assert three["answer_key"]["request"]["transaction_count"] == 3
    five = tree(post(client, seed="rows", transactions=rows, transaction_count=5))
    amounts = text(five, f"{PMT_INF}/CdtTrfTxInf/Amt/InstdAmt")
    assert (len(amounts), amounts[0], amounts[2]) == (5, "12.34", "56.78")
    assert [error["field"] for error in problems(client, transactions=rows, transaction_count=2)] == [
        "transaction_count"
    ]


def test_a_supplied_debtor_country_overrides_the_first_country(client: TestClient) -> None:
    document = tree(post(client, seed="debtor", payment={"debtor": {"address": {"country": "PL"}}}))
    assert text(document, f"{PMT_INF}/Dbtr/PstlAdr/Ctry") == ["PL"]
    assert text(document, f"{PMT_INF}/DbtrAgt/FinInstnId/BIC")[0][4:6] == "PL"
    assert text(document, f"{PMT_INF}/DbtrAcct/Id/IBAN")[0][:2] == "PL"


def test_supplied_addresses_accept_any_iso_country(client: TestClient) -> None:
    document = tree(post(client, seed="ch", transactions=[{"creditor": {"address": {"country": "CH"}}}]))
    assert text(document, f"{PMT_INF}/CdtTrfTxInf/Cdtr/PstlAdr/Ctry") == ["CH"]


V03, V09, V12 = "pain.001.001.03", "pain.001.001.09", "pain.001.001.12"
LONG = "x" * 71


@pytest.mark.parametrize(
    ("version", "row", "field", "says"),
    [
        (V12, {"creditor": {"name": "x" * 141}}, "transactions[0].creditor.name", "140"),
        (V03, {"creditor": {"address": {"street": LONG}}}, "transactions[0].creditor.address.street", V03),
        (V09, {"creditor": {"address": {"town": "x" * 36}}}, "transactions[0].creditor.address.town", V09),
        (V03, {"creditor_agent": {"bic": "DEUTDE1F"}}, "transactions[0].creditor_agent.bic", V03),
        (V12, {"creditor_agent": {"bic": "DEUTD1FF"}}, "transactions[0].creditor_agent.bic", "pattern"),
        (V12, {"creditor": {"address": {"country": "XX"}}}, "transactions[0].creditor.address.country", "3166"),
        (V12, {"currency": "XXY"}, "transactions[0].currency", "4217"),
        (
            V12,
            {"creditor_account": {"iban": "DE89370400440532013001"}},
            "transactions[0].creditor_account.iban",
            "IBAN",
        ),
        (V12, {"creditor_account": {"other_id": "1" * 35}}, "transactions[0].creditor_account.other_id", "34"),
        (V03, {"creditor_agent": {"lei": "529900T8BM49AURSDO55"}}, "transactions[0].creditor_agent.lei", ".09"),
        (V03, {"creditor": {"address": {"floor": "3"}}}, "transactions[0].creditor.address.floor", V03),
        (V09, {"creditor": {"address": {"care_of": "Ann"}}}, "transactions[0].creditor.address.care_of", V09),
        (V09, {"intermediary_agents": [{}, {"lei": "x"}]}, "transactions[0].intermediary_agents[1].lei", "pattern"),
    ],
)
def test_supplied_values_are_validated_for_the_message_version(
    client: TestClient, version: str, row: dict, field: str, says: str
) -> None:
    (error,) = problems(client, message_version=version, transactions=[row])
    assert error["field"] == field
    assert says in error["message"]


@pytest.mark.parametrize(
    ("version", "row"),
    [
        (V09, {"creditor_agent": {"bic": "DEUTDE1F", "lei": "529900T8BM49AURSDO55"}}),
        (V09, {"creditor": {"address": {"floor": "3", "town": "x" * 35}}}),
        (V12, {"creditor": {"address": {"street": LONG, "town": "x" * 140}}}),
    ],
)
def test_values_a_version_lacks_are_accepted_where_it_has_them(client: TestClient, version: str, row: dict) -> None:
    post(client, message_version=version, transactions=[row])


@pytest.mark.parametrize("version", [V09, "pain.001.001.13"])
def test_every_supplied_value_is_rendered_and_none_is_dropped(client: TestClient, version: str) -> None:
    address = {
        "street": "Bahnhofstrasse",
        "building_number": "1",
        "building_name": "Tower",
        "floor": "3",
        "post_box": "PB 7",
        "room": "301",
        "postcode": "8001",
        "town": "Zurich",
        "town_location_name": "Altstadt",
        "district_name": "Kreis 1",
        "country_subdivision": "ZH",
        "country": "CH",
    }
    payment = {
        "payment_information_id": "PMT-OURS",
        "debtor": {"name": "Debtor AG", "id": {"other_id": "CHE-123", "scheme": "TXID"}, "country_of_residence": "CH"},
        "debtor_agent": {"bic": "UBSWCHZH80A", "name": "UBS", "lei": "BFM8T61CT2L1QCEMIK50"},
        "debtor_account": {"iban": "CH9300762011623852957"},
    }
    row = {
        "end_to_end_id": "E2E-OURS",
        "creditor": {"name": "Creditor GmbH", "address": address},
        "creditor_agent": {"bic": "COBADEFFXXX", "address": {"lines": ["Kaiserplatz", "Frankfurt"], "country": "DE"}},
        "creditor_account": {"other_id": "0532013000", "scheme": "BBAN"},
        "amount": "1234.50",
        "currency": "CHF",
        "ultimate_debtor": {"name": "Parent Holding"},
        "ultimate_creditor": {"name": "Beneficiary Ltd"},
        "intermediary_agents": [{"bic": "DEUTDEFF"}, {"name": "Second Bank", "bic": None}],
        "remittance": {
            "unstructured": ["Line one", "Line two"],
            "structured": {
                "creditor_reference": "RF18539007547034",
                "invoicer": "Invoicer Co",
                "invoicee": "Invoicee Co",
                "additional": ["a", "b", "c"],
            },
        },
    }
    envelope = post(client, seed="all", message_version=version, payment=payment, transactions=[row])
    xml = envelope["sample_file"]["xml"]
    tx = f"{PMT_INF}/CdtTrfTxInf[1]"
    document = tree(envelope)

    assert envelope["answer_key"]["warnings"] == []
    assert text(document, f"{PMT_INF}/PmtInfId") == ["PMT-OURS"]
    assert text(document, f"{PMT_INF}/Dbtr/Id/OrgId/Othr/SchmeNm/Cd") == ["TXID"]
    assert text(document, f"{PMT_INF}/Dbtr/CtryOfRes") == ["CH"]
    assert text(document, f"{PMT_INF}/DbtrAgt/FinInstnId/LEI") == ["BFM8T61CT2L1QCEMIK50"]
    assert text(document, f"{PMT_INF}/DbtrAcct/Id/IBAN") == ["CH9300762011623852957"]
    assert text(document, f"{tx}/Amt/InstdAmt") == ["1234.50"]
    assert resolve(document, f"{tx}/Amt/InstdAmt")[0].get("Ccy") == "CHF"
    assert text(document, f"{tx}/CdtrAgt/FinInstnId/PstlAdr/AdrLine") == ["Kaiserplatz", "Frankfurt"]
    assert text(document, f"{tx}/CdtrAcct/Id/Othr/SchmeNm/Cd") == ["BBAN"]
    assert text(document, f"{tx}/IntrmyAgt2/FinInstnId/Nm") == ["Second Bank"]
    assert resolve(document, f"{tx}/IntrmyAgt2/FinInstnId/BICFI") == []
    assert text(document, f"{tx}/RmtInf/Ustrd") == ["Line one", "Line two"]
    assert text(document, f"{tx}/RmtInf/Strd/AddtlRmtInf") == ["a", "b", "c"]
    for value in [*address.values(), "E2E-OURS", "Parent Holding", "Beneficiary Ltd", "Invoicer Co", "Invoicee Co"]:
        assert f">{value}<" in xml, value


FULL_ROW = {
    "creditor": {"name": "Supplied Creditor"},
    "creditor_agent": {"name": "Supplied Bank"},
    "ultimate_debtor": None,
    "ultimate_creditor": None,
    "intermediary_agents": None,
    "remittance": {"unstructured": ["Supplied"]},
}
"""A row that supplies every role a Hit can take."""


def test_a_hit_on_supplied_data_wins_and_records_what_it_displaced(client: TestClient) -> None:
    payment = {"debtor": {"name": "Our Debtor"}, "debtor_agent": {"bic": "DEUTDEFF"}}
    key = post(client, seed="forced-0", transaction_count=1, hit_count=3, payment=payment)["answer_key"]

    displaced = {hit["placement"]: hit["displaced"] for hit in key["hits"] if hit["scope"] == "file"}
    assert displaced == {
        "debtor": {"field": "payment.debtor", "value": {"name": "Our Debtor"}},
        "debtor_agent": {"field": "payment.debtor_agent", "value": {"bic": "DEUTDEFF"}},
    }


@pytest.mark.parametrize("seed", [f"prefer-{n}" for n in range(8)])
def test_drawn_hits_prefer_transactions_whose_target_was_not_supplied(client: TestClient, seed: str) -> None:
    key = post(client, seed=seed, transactions=[FULL_ROW] * 5, transaction_count=10, hit_count=5)["answer_key"]

    for hit in key["hits"]:
        assert hit["displaced"] is None, hit
        assert hit["scope"] == "file" or hit["transaction_number"] > 5, hit


def test_drawn_hits_fall_back_to_supplied_transactions_when_there_is_no_room(client: TestClient) -> None:
    key = post(client, seed="no-room", transactions=[FULL_ROW] * 4, hit_count=4)["answer_key"]

    tx_hits = [hit for hit in key["hits"] if hit["scope"] == "transaction"]
    assert tx_hits
    for hit in tx_hits:
        assert hit["displaced"]["field"].startswith(f"transactions[{hit['transaction_number'] - 1}].")


@pytest.mark.parametrize(
    ("row", "field"),
    [
        ({"creditor": {"name": "pjsc rosneft oil company"}}, "transactions[0].creditor.name"),
        ({"creditor_agent": {"bic": "SABRRUMM"}}, "transactions[0].creditor_agent.bic"),
    ],
)
def test_supplied_data_cannot_name_a_catalogue_entity(client: TestClient, row: dict, field: str) -> None:
    assert [error["field"] for error in problems(client, transactions=[row])] == [field]


def test_a_named_hit_pinned_to_a_supplied_row_displaces_it(client: TestClient) -> None:
    named = [{"entity": "rosneft", "placement": "creditor", "transaction": 2}]
    rows = [{}, {"creditor": {"name": "Supplied Creditor"}}]
    key = post(client, seed="pinned", transactions=rows, hit_count=1, hits=named)["answer_key"]

    (hit,) = key["hits"]
    assert hit["displaced"] == {"field": "transactions[1].creditor", "value": {"name": "Supplied Creditor"}}


@pytest.mark.parametrize("seed", [f"exposed-{n}" for n in range(4)])
def test_exposures_prefer_transactions_whose_creditor_side_was_not_supplied(client: TestClient, seed: str) -> None:
    rows = [{"creditor": {"name": "Supplied Creditor"}}] * 5
    envelope = post(client, seed=seed, transactions=rows, transaction_count=10, exposure_count=5)

    assert sorted(e["transaction_number"] for e in envelope["answer_key"]["exposures"]) == [6, 7, 8, 9, 10]
    assert text(tree(envelope), f"{PMT_INF}/CdtTrfTxInf/Cdtr/Nm")[:5] == ["Supplied Creditor"] * 5
