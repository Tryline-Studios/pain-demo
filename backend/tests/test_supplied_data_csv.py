"""`POST /api/v1/sample-files/csv`: Supplied Data as a flat CSV beside a JSON `request` part (spec 5.6, 12.1)."""

import json

import httpx2
from fastapi.testclient import TestClient

FIXED = {"created_at": "2026-11-12T09:30:00Z", "execution_date": "2026-11-13"}


def post_csv(client: TestClient, csv: str, query: str = "", /, **request: object) -> httpx2.Response:
    return client.post(
        f"/api/v1/sample-files/csv{query}",
        data={"request": json.dumps({**FIXED, **request})},
        files={"supplied_data": ("data.csv", csv.encode(), "text/csv")},
    )


def problems(client: TestClient, csv: str, **request: object) -> list[dict]:
    response = post_csv(client, csv, **request)
    assert response.status_code == 422, response.text
    return response.json()["errors"]


ROUND_TRIP_CSV = (
    "payment.debtor.name,payment.debtor_agent.bic,end_to_end_id,creditor.name,creditor.address.country,"
    "creditor.address.lines.0,creditor.address.lines.1,amount,currency,intermediary_agents.0.bic,"
    "remittance.unstructured.0,creditor.id.other_id\n"
    "Ada Works Ltd,NWBKGB2L,E2E-1,Acme GmbH,DE,Hauptstr. 1,10115 Berlin,120.50,EUR,COBADEFF,Invoice 7,ACME-1\n"
    ",,E2E-2,Beta BV,,,,99.00,,,,\n"
)
ROUND_TRIP_JSON = {
    "payment": {"debtor": {"name": "Ada Works Ltd"}, "debtor_agent": {"bic": "NWBKGB2L"}},
    "transactions": [
        {
            "end_to_end_id": "E2E-1",
            "creditor": {
                "name": "Acme GmbH",
                "address": {"country": "DE", "lines": ["Hauptstr. 1", "10115 Berlin"]},
                "id": {"other_id": "ACME-1"},
            },
            "amount": "120.50",
            "currency": "EUR",
            "intermediary_agents": [{"bic": "COBADEFF"}],
            "remittance": {"unstructured": ["Invoice 7"]},
        },
        {"end_to_end_id": "E2E-2", "creditor": {"name": "Beta BV"}, "amount": "99.00"},
    ],
}


def test_the_same_supplied_data_as_csv_and_as_json_yields_the_same_sample_file(client: TestClient) -> None:
    settings = {**FIXED, "seed": "round-trip", "transaction_count": 4, "hit_count": 2}
    from_json = client.post("/api/v1/sample-files", json={**settings, **ROUND_TRIP_JSON})
    from_csv = post_csv(client, ROUND_TRIP_CSV, **settings)

    assert from_json.status_code == 200, from_json.text
    assert from_csv.status_code == 200, from_csv.text
    assert from_csv.json()["sample_file"]["xml"] == from_json.json()["sample_file"]["xml"]
    assert from_csv.json()["answer_key"] == from_json.json()["answer_key"]


def test_an_unknown_column_is_a_422_naming_it(client: TestClient) -> None:
    errors = problems(client, "creditor.name,creditor.nickname,intermediary_agents.x.bic\nAcme,Ace,\n")

    assert [e["field"] for e in errors] == [
        "supplied_data.creditor.nickname",
        "supplied_data.intermediary_agents.x.bic",
    ]
    assert "unknown column" in errors[0]["message"]


def test_payment_columns_come_from_the_first_row_and_later_rows_match_or_are_blank(client: TestClient) -> None:
    csv = "payment.debtor.name,creditor.name\nAda Works Ltd,Acme\nAda Works Ltd,Beta\n,Gamma\nOther Ltd,Delta\n"
    errors = problems(client, csv)

    assert [e["field"] for e in errors] == ["supplied_data[4].payment.debtor.name"]


def test_supplied_data_errors_name_the_row_and_column(client: TestClient) -> None:
    csv = "payment.debtor_agent.bic,creditor.name,currency\nNOTABIC,Acme,EUR\n,Beta,XXQ\n"
    errors = problems(client, csv)

    assert {e["field"] for e in errors} == {"supplied_data[1].payment.debtor_agent.bic", "supplied_data[2].currency"}


def test_version_and_catalogue_checks_apply_as_for_json(client: TestClient) -> None:
    lei = problems(client, "intermediary_agents.0.lei\n5493001KJTIIGC8Y1R12\n")
    entity = problems(client, "creditor.name\nAcme\nAlrosa\n")

    assert [e["field"] for e in lei] == ["supplied_data[1].intermediary_agents.0.lei"]
    assert "pain.001.001.03" in lei[0]["message"]
    assert [(e["field"], e["code"]) for e in entity] == [("supplied_data[2].creditor.name", "catalogue_entity")]


def test_the_request_part_carries_no_supplied_data(client: TestClient) -> None:
    errors = problems(client, "creditor.name\nAcme\n", transactions=[{}])

    assert [e["field"] for e in errors] == ["request.transactions"]


def test_zip_format_pads_rows_beyond_the_supplied_ones(client: TestClient) -> None:
    response = post_csv(client, "creditor.name\nAcme\n", "?format=zip", seed="zip", transaction_count=3)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"


def test_options_publish_a_header_template_the_endpoint_accepts(client: TestClient) -> None:
    columns = client.get("/api/v1/options").json()["supplied_data_columns"]

    assert columns[0] == "payment.payment_information_id"
    for column in (
        "creditor.name",
        "creditor.address.lines.0",
        "intermediary_agents.0.bic",
        "remittance.unstructured.0",
    ):
        assert column in columns
    assert post_csv(client, ",".join(columns) + "\n", seed="template").status_code == 200
