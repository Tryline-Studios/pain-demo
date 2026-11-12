"""`POST /api/v1/sample-files` with generation settings only: a clean Sample File and Answer Key (spec 5, 9, 11, 12)."""

import hashlib
import io
import json
import re
import zipfile
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from lxml import etree
from rapidfuzz import process, utils
from rapidfuzz.distance import JaroWinkler
from sample_files import assert_valid_sample_file
from schwifty import IBAN
from test_clean_banks import scratch_catalogue

from pain_demo.app import create_app
from pain_demo.catalogue import load_catalogue
from pain_demo.generation.clean_banks import SUPPORTED_COUNTRIES as COUNTRIES
from pain_demo.generation.clean_banks import load_clean_banks
from pain_demo.generation.generated_data import GeneratedData
from pain_demo.generation.model import SampleFileModel
from pain_demo.generation.sample_file import AnswerKey, answer_key_json
from pain_demo.renderer import RenderFailed
from pain_demo.settings import Settings
from pain_demo.validation import MESSAGE_VERSIONS
from pain_demo.version import app_version

CATALOGUE = load_catalogue()
CLEAN_BANKS = load_clean_banks(CATALOGUE)


def generate(client: TestClient, **settings: object) -> dict:
    response = client.post("/api/v1/sample-files", json=settings)
    assert response.status_code == 200, response.text
    envelope = response.json()
    assert_valid_sample_file(xml_of(envelope), envelope["answer_key"]["message_version"])
    return envelope


def xml_of(envelope: dict) -> bytes:
    return envelope["sample_file"]["xml"].encode("utf-8")


def tree(envelope: dict) -> etree._Element:
    return etree.fromstring(xml_of(envelope))


def texts(envelope: dict, path: str) -> list[str]:
    """Text of every element at a namespace-free path such as `PmtInf/CdtTrfTxInf/Cdtr/Nm`."""
    steps = "/".join(f"*[local-name()='{step}']" for step in path.split("/"))
    return [str(e.text) for e in tree(envelope).xpath(f"/*/*/{steps}")]


def test_an_empty_request_gets_a_valid_clean_file_with_every_default(client: TestClient) -> None:
    envelope = generate(client)

    seed = envelope["answer_key"]["seed"]
    assert re.fullmatch(r"[0-9a-f]{16}", seed)
    assert envelope["sample_file"]["filename"] == f"pain.001.001.03-{seed}.xml"
    assert envelope["sample_file"]["content_type"] == "application/xml"
    assert_valid_sample_file(xml_of(envelope), "pain.001.001.03")
    assert len(texts(envelope, "PmtInf/CdtTrfTxInf/PmtId/EndToEndId")) == 10
    assert envelope["answer_key"]["request"]["seed"] == seed
    assert envelope["answer_key"]["generator"]["app_version"] == app_version()


def test_replaying_the_effective_request_reproduces_the_file_and_answer_key_byte_for_byte(client: TestClient) -> None:
    first = generate(client, transaction_count=25, countries=["DE", "IT", "US"])

    replayed = generate(client, **first["answer_key"]["request"])

    assert replayed == first


def test_the_effective_request_resolves_every_default(client: TestClient) -> None:
    request = generate(client, seed="regression-run-42")["answer_key"]["request"]

    assert request["seed"] == "regression-run-42"
    assert request["message_version"] == "pain.001.001.03"
    assert request["transaction_count"] == 10
    assert request["countries"] == ["GB", "DE", "FR", "NL", "US"]
    assert request["currencies"] is None
    assert (request["amount_min"], request["amount_max"]) == ("10.00", "50000.00")
    assert re.fullmatch(r"MSG-[0-9A-F]{12}", request["message_id"])
    assert request["created_at"]
    assert request["execution_date"]
    assert request["hit_count"] == 0


def test_a_transaction_is_the_same_whether_the_file_holds_10_or_100(client: TestClient) -> None:
    settings = {"seed": "stable-rows", "created_at": "2026-11-12T09:30:00Z", "execution_date": "2026-11-13"}
    small = tree(generate(client, transaction_count=10, **settings))
    large = tree(generate(client, transaction_count=100, **settings))

    def third(document: etree._Element) -> bytes:
        return etree.tostring(document.xpath("//*[local-name()='CdtTrfTxInf'][3]")[0])

    assert third(small) == third(large)


@pytest.mark.parametrize("message_version", MESSAGE_VERSIONS)
def test_every_message_version_gets_a_valid_file(client: TestClient, message_version: str) -> None:
    envelope = generate(client, message_version=message_version, transaction_count=100, countries=list(COUNTRIES))

    assert_valid_sample_file(xml_of(envelope), message_version)
    assert envelope["answer_key"]["message_version"] == message_version
    assert envelope["answer_key"]["warnings"] == []


def test_the_file_starts_with_a_comment_carrying_the_seed_and_app_version(client: TestClient) -> None:
    lines = generate(client, seed="regression-run-42")["sample_file"]["xml"].splitlines()

    assert lines[0] == "<?xml version='1.0' encoding='UTF-8'?>"
    assert lines[1] == f'<!-- pain-demo {app_version()} seed="regression-run-42" -->'


@pytest.mark.parametrize("seed", ["a--b", "trailing-", "--", 'quote " and \\ back', "naïve\tseed"])
def test_any_seed_keeps_the_comment_well_formed_and_recoverable(client: TestClient, seed: str) -> None:
    envelope = generate(client, seed=seed)

    document = etree.fromstring(xml_of(envelope))
    (comment,) = [node for node in document.itersiblings(preceding=True) if isinstance(node, etree._Comment)]
    assert json.loads(str(comment.text).split("seed=", 1)[1].strip()) == seed
    assert envelope["answer_key"]["seed"] == envelope["answer_key"]["request"]["seed"] == seed
    assert_valid_sample_file(xml_of(envelope), "pain.001.001.03")


@pytest.mark.parametrize(
    ("seed", "name"),
    [
        ("regression-run-42", "pain.001.001.09-regression-run-42.xml"),
        ("v1.2_rc", "pain.001.001.09-v1.2_rc.xml"),
        ("a b/c", f"pain.001.001.09-{hashlib.sha256(b'a b/c').hexdigest()[:16]}.xml"),
    ],
)
def test_the_filename_is_the_version_and_a_filename_safe_seed(client: TestClient, seed: str, name: str) -> None:
    envelope = generate(client, seed=seed, message_version="pain.001.001.09")

    assert envelope["sample_file"]["filename"] == name


def test_the_answer_key_describes_the_clean_file(client: TestClient) -> None:
    envelope = generate(
        client,
        seed="key",
        transaction_count=3,
        message_id="MSG-FIXED",
        created_at="2026-11-12T09:30:00Z",
        execution_date="2026-11-13",
    )
    key = envelope["answer_key"]

    assert list(key) == [
        "answer_key_version",
        "seed",
        "message_version",
        "generator",
        "request",
        "file",
        "summary",
        "hits",
        "exposures",
        "transactions",
        "warnings",
    ]
    assert key["answer_key_version"] == 1
    assert key["generator"] == client.get("/api/v1/version").json()
    assert key["file"] == {
        "message_id": "MSG-FIXED",
        "created_at": "2026-11-12T09:30:00Z",
        "execution_date": "2026-11-13",
        "transaction_count": 3,
        "hit_count": 0,
        "sha256": hashlib.sha256(xml_of(envelope)).hexdigest(),
    }
    assert key["summary"] == {
        "by_placement": {},
        "by_name_variant": {},
        "by_entity_type": {},
        "by_list": {},
        "by_exposure_country": {},
    }
    assert (key["hits"], key["exposures"], key["warnings"]) == ([], [], [])
    end_to_end_ids = texts(envelope, "PmtInf/CdtTrfTxInf/PmtId/EndToEndId")
    assert key["transactions"] == [
        {"number": n, "end_to_end_id": e2e, "hit_ids": []} for n, e2e in enumerate(end_to_end_ids, start=1)
    ]
    assert texts(envelope, "GrpHdr/MsgId") == ["MSG-FIXED"]
    assert texts(envelope, "GrpHdr/CreDtTm") == ["2026-11-12T09:30:00+00:00"]
    assert texts(envelope, "PmtInf/ReqdExctnDt") == ["2026-11-13"]


def transactions_of(envelope: dict) -> list[etree._Element]:
    return tree(envelope).xpath("//*[local-name()='CdtTrfTxInf']")


def text_at(element: etree._Element, path: str) -> list[str]:
    steps = "/".join(f"*[local-name()='{step}']" for step in path.split("/"))
    return [str(e.text) for e in element.xpath(steps)]


def test_the_debtor_takes_the_first_country_and_creditors_draw_from_all(client: TestClient) -> None:
    envelope = generate(client, seed="countries", transaction_count=100, countries=["PL", "US", "IT"])

    assert texts(envelope, "PmtInf/Dbtr/PstlAdr/Ctry") == ["PL"]
    assert texts(envelope, "PmtInf/DbtrAcct/Id/IBAN")[0].startswith("PL")
    assert texts(envelope, "GrpHdr/InitgPty/Nm") == texts(envelope, "PmtInf/Dbtr/Nm")
    creditor_countries = texts(envelope, "PmtInf/CdtTrfTxInf/Cdtr/PstlAdr/Ctry")
    assert set(creditor_countries) == {"PL", "US", "IT"}


def test_currency_follows_the_creditor_country_unless_currencies_are_given(client: TestClient) -> None:
    by_country = generate(client, seed="ccy", transaction_count=60, countries=list(COUNTRIES))
    expected = {"GB": "GBP", "US": "USD", "PL": "PLN"}
    for tx in transactions_of(by_country):
        (country,) = text_at(tx, "Cdtr/PstlAdr/Ctry")
        (amount,) = tx.xpath("*[local-name()='Amt']/*[local-name()='InstdAmt']")
        assert amount.get("Ccy") == expected.get(country, "EUR")

    drawn = generate(client, seed="ccy", transaction_count=60, currencies=["CHF", "JPY"])
    assert {a.get("Ccy") for a in tree(drawn).xpath("//*[local-name()='InstdAmt']")} == {"CHF", "JPY"}


def test_amounts_are_two_decimal_values_in_range(client: TestClient) -> None:
    envelope = generate(client, seed="amounts", transaction_count=100, amount_min="5.50", amount_max="7.25")

    amounts = [Decimal(a) for a in texts(envelope, "PmtInf/CdtTrfTxInf/Amt/InstdAmt")]
    assert all(Decimal("5.50") <= a <= Decimal("7.25") for a in amounts)
    assert all(re.fullmatch(r"[0-9]+\.[0-9]{2}", a) for a in texts(envelope, "PmtInf/CdtTrfTxInf/Amt/InstdAmt"))


def test_us_creditors_get_an_other_account_and_an_aba_routed_agent(client: TestClient) -> None:
    envelope = generate(client, seed="us", transaction_count=5, countries=["US"])
    us_routing = {bank.bic: bank.routing_number for bank in CLEAN_BANKS.for_country("US")}

    for tx in transactions_of(envelope):
        assert text_at(tx, "CdtrAcct/Id/IBAN") == []
        assert re.fullmatch(r"[0-9]{10}", text_at(tx, "CdtrAcct/Id/Othr/Id")[0])
        assert text_at(tx, "CdtrAcct/Id/Othr/SchmeNm/Prtry") == []
        (bic,) = text_at(tx, "CdtrAgt/FinInstnId/BIC")
        assert text_at(tx, "CdtrAgt/FinInstnId/ClrSysMmbId/MmbId") == [us_routing[bic]]
        assert text_at(tx, "CdtrAgt/FinInstnId/ClrSysMmbId/ClrSysId/Cd") == ["USABA"]


def test_every_agent_and_iban_comes_from_the_clean_bank_list(client: TestClient) -> None:
    envelope = generate(client, seed="banks", transaction_count=100, countries=list(COUNTRIES))
    clean = {bank.bic: bank for bank in CLEAN_BANKS.banks}

    document = tree(envelope)
    agents = document.xpath("//*[local-name()='FinInstnId']")
    assert agents
    for agent in agents:
        (bic,) = text_at(agent, "BIC")
        assert text_at(agent, "Nm") == [clean[bic].name]
    for iban in document.xpath("//*[local-name()='IBAN']/text()"):
        parsed = IBAN(str(iban))
        assert parsed.bank_code in {b.bank_code for b in clean.values() if b.country == parsed.country_code}


def test_optional_roles_appear_at_their_background_rates(client: TestClient) -> None:
    envelope = generate(client, seed="background", transaction_count=100)

    def count(element: str) -> int:
        return len(tree(envelope).xpath(f"//*[local-name()='CdtTrfTxInf']/*[local-name()='{element}']"))

    assert 4 <= count("UltmtCdtr") <= 18
    assert 1 <= count("UltmtDbtr") <= 11
    assert 1 <= count("IntrmyAgt1") <= 11
    assert count("IntrmyAgt2") == 0
    assert 7 <= len(texts(envelope, "PmtInf/CdtTrfTxInf/RmtInf/Strd/CdtrRefInf/Ref")) <= 25
    assert tree(envelope).xpath("/*/*/*[local-name()='PmtInf']/*[local-name()='UltmtDbtr']") == []


def test_no_generated_party_name_resembles_a_catalogue_name(client: TestClient) -> None:
    envelope = generate(client, seed="screened", transaction_count=100, countries=list(COUNTRIES))
    catalogue_names = [n.value for e in CATALOGUE.entities.values() for n in e.names]

    # Agent names come from the Clean Bank List, which startup checks instead (spec 4.3).
    party_names = "//*[local-name()='Nm'][not(parent::*[local-name()='FinInstnId'])]/text()"
    names = {str(n) for n in tree(envelope).xpath(party_names)}
    assert len(names) > 100
    for name in names:
        best = process.extractOne(
            name, catalogue_names, scorer=JaroWinkler.normalized_similarity, processor=utils.default_process
        )
        assert best is not None
        assert best[1] < 0.85, (name, best)


@pytest.mark.parametrize(
    ("settings", "field", "code"),
    [
        ({"transaction_count": 0}, "transaction_count", "greater_than_equal"),
        ({"transaction_count": 101}, "transaction_count", "less_than_equal"),
        ({"countries": ["GB", "RU"]}, "countries[1]", "literal_error"),
        ({"countries": []}, "countries", "too_short"),
        ({"currencies": ["EUR", "XX"]}, "currencies[1]", "string_pattern_mismatch"),
        ({"currencies": ["ABC"]}, "currencies[0]", "value_error"),
        ({"seed": "s" * 65}, "seed", "string_too_long"),
        ({"amount_min": "1.001"}, "amount_min", "decimal_max_places"),
        ({"amount_min": "0"}, "amount_min", "greater_than"),
        ({"amount_min": "100", "amount_max": "99.99"}, "amount_max", "value_error"),
        ({"message_version": "pain.001.001.02"}, "message_version", "literal_error"),
        ({"message_id": "M" * 36}, "message_id", "string_too_long"),
        ({"hit_count": -1}, "hit_count", "greater_than_equal"),
        ({"transaction_count": 3, "hit_count": 6}, "hit_count", "value_error"),
        ({"hit_count": 13}, "hit_count", "value_error"),
        ({"hits": [{"entity": "sberbank", "transaction": 0}]}, "hits[0].transaction", "greater_than_equal"),
        ({"placements": ["teller"]}, "placements[0]", "literal_error"),
    ],
)
def test_invalid_settings_are_422_problems_naming_the_field(
    client: TestClient, settings: dict, field: str, code: str
) -> None:
    response = client.post("/api/v1/sample-files", json=settings)

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    problem = response.json()
    assert problem["type"] == "validation_error"
    assert [(e["field"], e["code"]) for e in problem["errors"]] == [(field, code)]


def test_a_build_failure_is_a_500_problem_and_logs_the_effective_request(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def failing_render(model: object) -> object:
        raise RenderFailed([".../Cdtr/Nm: value length cannot be greater than 140"])

    monkeypatch.setattr("pain_demo.generation.sample_file.render", failing_render)
    with TestClient(create_app(Settings(log_format="json", log_level="INFO"))) as client:
        response = client.post("/api/v1/sample-files", json={"seed": "broken"}, headers={"X-Request-Id": "req-b"})

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    problem = response.json()
    assert (problem["type"], problem["instance"]) == ("build_failed", "req-b")
    assert "value length cannot be greater than 140" in problem["detail"]
    assert set(problem) == {"type", "title", "status", "detail", "instance"}
    assert "broken" not in response.text
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    (failure,) = [e for e in events if e["event"] == "build_failed"]
    assert failure["level"] == "error"
    assert failure["request_id"] == "req-b"
    assert failure["xsd_messages"] == [".../Cdtr/Nm: value length cannot be greater than 140"]
    assert failure["effective_request"]["seed"] == "broken"
    assert failure["effective_request"]["message_version"] == "pain.001.001.03"
    assert failure["effective_request"]["transaction_count"] == 10
    (request_event,) = [e for e in events if e["event"] == "request"]
    assert (request_event["outcome"], request_event["status"]) == ("build_failed", 500)


def test_generated_data_the_message_version_cannot_hold_is_an_answer_key_warning(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    draw = GeneratedData.sample_file_model

    def draw_with_debtor_agent_lei(self: GeneratedData) -> SampleFileModel:
        model = draw(self)
        return replace(model, debtor_agent=replace(model.debtor_agent, lei="851WYGNLUQLFZBSYGB56"))

    # Generated Data has no LEI yet; this stands in for any element older Message Versions cannot carry.
    monkeypatch.setattr(GeneratedData, "sample_file_model", draw_with_debtor_agent_lei)
    with TestClient(create_app(Settings(log_format="json", log_level="INFO"))) as client:
        old = generate(client, seed="lei", message_version="pain.001.001.03")
        new = generate(client, seed="lei", message_version="pain.001.001.09")

    assert old["answer_key"]["warnings"] == [
        "/Document/CstmrCdtTrfInitn/PmtInf/DbtrAgt/FinInstnId/LEI dropped: not in pain.001.001.03"
    ]
    assert new["answer_key"]["warnings"] == []
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    assert [e["warning_count"] for e in events if e["event"] == "request"] == [1, 0]


def test_generation_logs_its_summary_but_no_content(capsys: pytest.CaptureFixture[str]) -> None:
    with TestClient(create_app(Settings(log_format="json", log_level="INFO"))) as client:
        envelope = generate(client, seed="logged", transaction_count=4, message_version="pain.001.001.09")

    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    (event,) = [e for e in events if e["event"] == "request"]
    assert {k: event[k] for k in ("message_version", "transaction_count", "hit_count", "seed", "outcome")} == {
        "message_version": "pain.001.001.09",
        "transaction_count": 4,
        "hit_count": 0,
        "seed": "logged",
        "outcome": "generated",
    }
    assert (event["named_hit_count"], event["data_source"], event["warning_count"]) == (0, "generated", 0)
    debtor = texts(envelope, "PmtInf/Dbtr/Nm")[0]
    assert debtor not in json.dumps(events)


def test_a_generated_name_matching_the_catalogue_is_redrawn(tmp_path: Path) -> None:
    settings = {"seed": "redraw", "transaction_count": 1, "countries": ["DE"]}
    with TestClient(create_app()) as client:
        drawn = texts(generate(client, **settings), "PmtInf/CdtTrfTxInf/Cdtr/Nm")[0]

    scratch_catalogue(tmp_path, {"lookalike": drawn.upper()}, {})
    with TestClient(create_app(catalogue_root=tmp_path)) as client:
        redrawn = texts(generate(client, **settings), "PmtInf/CdtTrfTxInf/Cdtr/Nm")[0]

    assert redrawn != drawn
    assert JaroWinkler.normalized_similarity(redrawn.upper(), drawn.upper()) < 0.85


ZIP_SETTINGS = {"seed": "zip-run", "created_at": "2026-11-12T09:30:00Z", "execution_date": "2026-11-13"}


def test_format_zip_returns_the_sample_file_and_answer_key_in_one_zip(client: TestClient) -> None:
    envelope = generate(client, **ZIP_SETTINGS)

    response = client.post("/api/v1/sample-files", params={"format": "zip"}, json=ZIP_SETTINGS)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"] == 'attachment; filename="pain.001.001.03-zip-run.zip"'
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.namelist() == [
            "pain.001.001.03-zip-run.xml",
            "pain.001.001.03-zip-run.answer-key.json",
            "pain.001.001.03-zip-run.answer-key.csv",
        ]
        xml = archive.read("pain.001.001.03-zip-run.xml").decode("utf-8")
        answer_key = archive.read("pain.001.001.03-zip-run.answer-key.json").decode("utf-8")
    assert xml == envelope["sample_file"]["xml"]
    assert json.loads(answer_key) == envelope["answer_key"]
    assert answer_key.startswith('{\n  "answer_key_version": 1,\n')
    assert answer_key.endswith("}\n")


def test_replaying_the_effective_request_as_a_zip_gives_the_same_files(client: TestClient) -> None:
    """The Workbench's zip download: it re-posts `answer_key.request` with `format=zip` (spec 13.4)."""
    envelope = generate(client, seed="Zürich ✓")

    response = client.post("/api/v1/sample-files", params={"format": "zip"}, json=envelope["answer_key"]["request"])

    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        xml_member, answer_key_member, _ = archive.namelist()
        xml = archive.read(xml_member).decode("utf-8")
        answer_key = archive.read(answer_key_member).decode("utf-8")
    assert xml == envelope["sample_file"]["xml"]
    assert answer_key == answer_key_json(AnswerKey.model_validate(envelope["answer_key"]))
    # The Workbench builds its Answer Key JSON download with `JSON.stringify(answer_key, null, 2) + "\n"`.
    assert answer_key == json.dumps(envelope["answer_key"], indent=2, ensure_ascii=False) + "\n"


def test_the_zip_is_byte_for_byte_reproducible(client: TestClient) -> None:
    first, second = (
        client.post("/api/v1/sample-files", params={"format": "zip"}, json=ZIP_SETTINGS).content for _ in range(2)
    )

    assert first == second


def test_an_unknown_format_is_a_422_naming_the_parameter(client: TestClient) -> None:
    response = client.post("/api/v1/sample-files", params={"format": "tar"}, json={})

    assert response.status_code == 422
    assert [e["field"] for e in response.json()["errors"]] == ["format"]


def test_message_versions_lists_the_eleven_with_the_default_flagged(client: TestClient) -> None:
    response = client.get("/api/v1/message-versions")

    assert response.status_code == 200
    assert response.json() == [
        {"message_version": version, "default": version == "pain.001.001.03"} for version in MESSAGE_VERSIONS
    ]


def test_options_publish_countries_limits_and_defaults(client: TestClient) -> None:
    options = client.get("/api/v1/options").json()

    assert options["countries"][:2] == [{"country": "GB", "currency": "GBP"}, {"country": "IE", "currency": "EUR"}]
    assert [c["country"] for c in options["countries"]] == list(COUNTRIES)
    assert options["limits"] == {"max_transactions": 100, "max_seed_length": 64}
    assert options["defaults"] == {
        "message_version": "pain.001.001.03",
        "transaction_count": 10,
        "countries": ["GB", "DE", "FR", "NL", "US"],
        "amount_min": "10.00",
        "amount_max": "50000.00",
        "exposure_countries": ["RU", "BY", "IR", "KP", "SY", "VE"],
    }


def test_options_publish_placements_name_variants_and_rendering_modes(client: TestClient) -> None:
    options = client.get("/api/v1/options").json()

    placements = {p["placement"]: p for p in options["placements"]}
    assert len(placements) == 10
    assert placements["debtor"] == {"placement": "debtor", "file_level": True, "agent": False}
    assert placements["debtor_agent"] == {"placement": "debtor_agent", "file_level": True, "agent": True}
    assert placements["remittance"] == {"placement": "remittance", "file_level": False, "agent": False}
    assert options["name_variants"] == ["exact", "alias", "native_script", "transliteration", "fuzzed"]
    assert options["rendering_modes"] == ["name_and_bic", "bic_only", "name_only"]
