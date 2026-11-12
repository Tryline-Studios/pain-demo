"""The Answer Key CSV: one row per Hit, from `POST /answer-keys/csv` and in the zip (spec 11.1, 12.1, 12.2)."""

import io
import zipfile

from fastapi.testclient import TestClient
from test_sample_files_api import ZIP_SETTINGS, generate

CSV_HITS = [
    {
        "id": "h1",
        "scope": "file",
        "xpath": "/Document/CstmrCdtTrfInitn/PmtInf/DbtrAgt/FinInstnId/BIC",
        "entity": {
            "id": "bank-rossiya",
            "entity_type": "bank",
            "listings": [{"list": "ofac_sdn", "entry_id": "1"}, {"list": "uk", "entry_id": "RUS0001"}],
        },
        "placement": "debtor_agent",
        "rendering_mode": "bic_only",
        "name": None,
        "bic": {"value": "ROSYRU2P", "source": "listing"},
        "lei": None,
        "address_from_listing": None,
        "triggers": [],
        "origin": "drawn",
        "paired_with": None,
        "displaced": None,
    },
    {
        "id": "h2",
        "scope": "transaction",
        "transaction_number": 2,
        "end_to_end_id": "E2E-2",
        "xpath": "/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf[2]/Cdtr/Nm",
        "entity": {"id": "ivan-petrov", "entity_type": "individual", "listings": [{"list": "uk", "entry_id": "X"}]},
        "placement": "creditor",
        "name": {
            "variant": "transliteration",
            "rendered": "Ivan Petrov",
            "source": {
                "value": "Иван Петров",
                "type": "aka",
                "script": "cyrillic",
                "listing": {"list": "uk", "entry_id": "X"},
            },
            "scheme": "icao",
        },
        "bic": None,
        "lei": None,
        "address_from_listing": None,
        "triggers": [],
        "origin": "named",
        "paired_with": "h3",
        "displaced": None,
    },
    {
        "id": "h3",
        "scope": "transaction",
        "transaction_number": 3,
        "end_to_end_id": "E2E-3",
        "xpath": "/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf[3]/RmtInf/Ustrd",
        "entity": {"id": "acme-corp", "entity_type": "corporate", "listings": [{"list": "ofac_sdn", "entry_id": "9"}]},
        "placement": "remittance",
        "element": "ustrd",
        "name": {
            "variant": "fuzzed",
            "rendered": 'Invoice 12, "ACME" Corp',
            "source": {
                "value": "ACME Corp LLC",
                "type": "primary",
                "script": "latin",
                "listing": {"list": "ofac_sdn", "entry_id": "9"},
            },
            "base": "ACME Corp LLC",
            "operations": ["drop_legal_form", "typo"],
        },
        "bic": None,
        "lei": None,
        "address_from_listing": None,
        "triggers": [],
        "origin": "drawn",
        "paired_with": None,
        "displaced": None,
    },
]

EXPECTED_CSV = (
    "hit_id,scope,transaction_number,end_to_end_id,entity_id,entity_type,lists,placement,element,rendering_mode,"
    "name_variant,rendered_text,source_value,source_type,scheme,operations,bic,origin,paired_hit,xpath\r\n"
    "h1,file,,,bank-rossiya,bank,ofac_sdn|uk,debtor_agent,,bic_only,,,,,,,ROSYRU2P,drawn,,"
    "/Document/CstmrCdtTrfInitn/PmtInf/DbtrAgt/FinInstnId/BIC\r\n"
    "h2,transaction,2,E2E-2,ivan-petrov,individual,uk,creditor,,,transliteration,Ivan Petrov,Иван Петров,aka,icao,,,"
    "named,h3,/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf[2]/Cdtr/Nm\r\n"
    'h3,transaction,3,E2E-3,acme-corp,corporate,ofac_sdn,remittance,ustrd,,fuzzed,"Invoice 12, ""ACME"" Corp",'
    "ACME Corp LLC,primary,,drop_legal_form|typo,,drawn,,"
    "/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf[3]/RmtInf/Ustrd\r\n"
)


def test_an_answer_key_becomes_a_csv_with_one_row_per_hit(client: TestClient) -> None:
    answer_key = {**generate(client, seed="csv")["answer_key"], "hits": CSV_HITS}

    response = client.post("/api/v1/answer-keys/csv", json=answer_key)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.text == EXPECTED_CSV


def test_an_answer_key_of_another_version_is_a_422(client: TestClient) -> None:
    answer_key = {**generate(client)["answer_key"], "answer_key_version": 2}

    response = client.post("/api/v1/answer-keys/csv", json=answer_key)

    assert response.status_code == 422
    assert [e["field"] for e in response.json()["errors"]] == ["answer_key_version"]


def test_the_zip_holds_the_answer_key_csv_the_transform_gives(client: TestClient) -> None:
    envelope = generate(client, **ZIP_SETTINGS, hit_count=4)
    expected = client.post("/api/v1/answer-keys/csv", json=envelope["answer_key"]).text

    response = client.post("/api/v1/sample-files", params={"format": "zip"}, json={**ZIP_SETTINGS, "hit_count": 4})

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        csv = archive.read("pain.001.001.03-zip-run.answer-key.csv").decode("utf-8")
    assert csv == expected
    assert len(csv.splitlines()) == 1 + 4
