"""The Clean Bank List: schema, the catalogue overlap assertion and `just build-clean-banks` (spec section 4)."""

import json
from pathlib import Path

import pytest

from pain_workbench.app import create_app
from pain_workbench.catalogue import Catalogue, load_catalogue
from pain_workbench.generation import build_clean_banks
from pain_workbench.generation.clean_banks import (
    DEFAULT_PATH,
    IBAN_COUNTRIES,
    CleanBankListError,
    load_clean_banks,
    normalise_name,
)
from pain_workbench.settings import Settings

# --- the committed list


def test_the_committed_list_passes_the_catalogue_assertion() -> None:
    clean_banks = load_clean_banks(load_catalogue())

    assert len(clean_banks) > 0


def test_the_committed_list_has_about_25_banks_per_iban_country_and_a_us_section() -> None:
    clean_banks = load_clean_banks(load_catalogue())

    for country in IBAN_COUNTRIES:
        banks = clean_banks.for_country(country)
        assert 15 <= len(banks) <= build_clean_banks.BANKS_PER_COUNTRY, country
        assert [bank.name for bank in banks] == sorted((bank.name for bank in banks), key=normalise_name), country
        assert all(bank.routing_number is None for bank in banks), country
    us_banks = clean_banks.for_country("US")
    assert len(us_banks) >= 10
    assert all(bank.routing_number is not None for bank in us_banks)
    assert len({bank.bic for bank in clean_banks.banks}) == len(clean_banks)


# --- the overlap assertion, on a scratch list


def bank_entry(country: str, bank_code: str, bic: str, name: str) -> str:
    return f"""
[[banks]]
country = "{country}"
bank_code = "{bank_code}"
bic = "{bic}"
name = "{name}"
"""


US_ENTRY = """
[[banks]]
country = "US"
bank_code = "021000021"
bic = "CHASUS33"
name = "JPMorgan Chase Bank, N.A."
routing_number = "021000021"
"""


def problems_of(toml: str, tmp_path: Path) -> list[str]:
    path = tmp_path / "clean_banks.toml"
    path.write_text(toml, encoding="utf-8")
    with pytest.raises(CleanBankListError) as raised:
        load_clean_banks(load_catalogue(), path)
    return raised.value.problems


def test_a_bank_sharing_a_catalogue_bic_is_refused(tmp_path: Path) -> None:
    problems = problems_of(bank_entry("AT", "19100", "SABRATWWXXX", "Some Other Name AG"), tmp_path)

    assert problems == ["AT SABRATWWXXX 'Some Other Name AG' shares a BIC with catalogue Entity 'sberbank-europe'"]


def test_a_bank_sharing_a_catalogue_normalised_name_is_refused(tmp_path: Path) -> None:
    problems = problems_of(bank_entry("DE", "20210200", "MELIDEHHXXX", "BANK MELLI-IRAN"), tmp_path)

    assert problems == ["DE MELIDEHHXXX 'BANK MELLI-IRAN' shares a name with catalogue Entity 'bank-melli-iran'"]


def test_a_clean_entry_is_accepted_beside_the_us_section(tmp_path: Path) -> None:
    path = tmp_path / "clean_banks.toml"
    path.write_text(bank_entry("DE", "37040044", "COBADEFFXXX", "Commerzbank AG") + US_ENTRY, encoding="utf-8")

    clean_banks = load_clean_banks(load_catalogue(), path)

    assert [bank.bic for bank in clean_banks.for_country("DE")] == ["COBADEFFXXX"]
    assert clean_banks.for_country("US")[0].routing_number == "021000021"
    assert clean_banks.for_country("GB") == []


WRONG_CHECK_DIGIT = US_ENTRY.replace('routing_number = "021000021"', 'routing_number = "021000022"')
CODE_IS_NOT_ROUTING = US_ENTRY.replace('bank_code = "021000021"', 'bank_code = "CHAS"')
GERMAN_WITH_ROUTING = bank_entry("DE", "37040044", "COBADEFFXXX", "Commerzbank AG") + 'routing_number = "021000021"\n'


@pytest.mark.parametrize(
    ("toml", "problem"),
    [
        (
            bank_entry("GB", "ABBY", "ABBYDE2LXXX", "Santander UK PLC"),
            "banks.0: Value error, BIC ABBYDE2LXXX is not a GB BIC",
        ),
        (
            bank_entry("US", "021000021", "CHASUS33", "Chase"),
            "banks.0: Value error, a US entry carries its ABA routing number",
        ),
        (WRONG_CHECK_DIGIT, "banks.0.routing_number: Value error, ABA routing number check digit does not hold"),
        (CODE_IS_NOT_ROUTING, "banks.0: Value error, a US entry's bank code is its ABA routing number"),
        (GERMAN_WITH_ROUTING, "banks.0: Value error, only US entries carry an ABA routing number"),
        (
            bank_entry("CH", "0001", "UBSWCHZH80A", "UBS"),
            "banks.0.country: Input should be 'GB', 'IE', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'PL', 'AT', 'PT' or 'US'",
        ),
    ],
)
def test_an_entry_must_be_well_formed(tmp_path: Path, toml: str, problem: str) -> None:
    assert problems_of(toml, tmp_path) == [f"clean_banks.toml: {problem}"]


def test_a_missing_list_is_a_problem(tmp_path: Path) -> None:
    with pytest.raises(CleanBankListError) as raised:
        load_clean_banks(load_catalogue(), tmp_path / "clean_banks.toml")

    assert raised.value.problems == ["clean_banks.toml: missing"]


def test_an_overlapping_list_logs_critical_and_exits_non_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "clean_banks.toml"
    path.write_text(bank_entry("AT", "19100", "SABRATWWXXX", "Sberbank Europe AG"), encoding="utf-8")

    with pytest.raises(SystemExit) as raised:
        create_app(Settings(log_format="json"), clean_banks_path=path)

    assert raised.value.code == 1
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    (event,) = events
    assert event["level"] == "critical"
    assert event["event"] == "clean_bank_list_invalid"
    assert event["problems"] == [
        "AT SABRATWWXXX 'Sberbank Europe AG' shares a BIC with catalogue Entity 'sberbank-europe'",
        "AT SABRATWWXXX 'Sberbank Europe AG' shares a name with catalogue Entity 'sberbank-europe'",
    ]


@pytest.mark.parametrize(
    ("name", "normalised"),
    [
        ("Bank Melli-Iran", "bank melli iran"),
        ("  Crédit   Agricole S.A. ", "credit agricole s a"),
        ("Sparkasse Köln/Bonn", "sparkasse koln bonn"),
        ('PJSC "Sberbank"', "pjsc sberbank"),
        ("ПАО Сбербанк", ""),
    ],
)
def test_names_are_normalised_for_comparison(name: str, normalised: str) -> None:
    assert normalise_name(name) == normalised


# --- just build-clean-banks


def scratch_catalogue(root: Path, bank_names: dict[str, str], bank_bics: dict[str, str]) -> Catalogue:
    """A catalogue of Banks named `bank_names[id]`, some with the BIC `bank_bics[id]`, on one OFAC Listing each."""
    (root / "entities").mkdir(parents=True)
    for entity_id, name in bank_names.items():
        entity = f"""
id = "{entity_id}"
entity_type = "bank"

[[listings]]
list = "ofac_sdn"
entry_id = "1"
programmes = ["RUSSIA-EO14024"]
designation_date = 2022-04-06
verified = {{ snapshot_date = 2026-09-14, source_file = "SDN_ADVANCED.XML" }}

[[names]]
value = "{name}"
source_type = "primary"
script = "latin"
script_source = "stated"
listing = {{ list = "ofac_sdn", entry_id = "1" }}
"""
        if bic := bank_bics.get(entity_id):
            entity += f"""
[[bics]]
value = "{bic}"
listing = {{ list = "ofac_sdn", entry_id = "1" }}
verified_date = 2026-09-14
"""
        (root / "entities" / f"{entity_id}.toml").write_text(entity, encoding="utf-8")
    (root / "control_relationships.toml").write_text("", encoding="utf-8")
    return load_catalogue(root)


def test_the_committed_iban_country_section_is_what_the_builder_writes() -> None:
    assert build_clean_banks.build(load_catalogue()) == DEFAULT_PATH.read_text(encoding="utf-8")


def test_the_builder_keeps_the_us_section_and_drops_catalogue_matches(tmp_path: Path) -> None:
    catalogue = scratch_catalogue(
        tmp_path / "catalogue",
        {"test-bank": "Commerzbank", "test-bank-2": "Test Bank Two"},
        {"test-bank-2": "ABBYGB2LXXX"},
    )
    path = tmp_path / "clean_banks.toml"
    us_section = f"{build_clean_banks.US_SECTION_MARKER} ---\n# a comment the builder must keep\n{US_ENTRY}"
    path.write_text("# stale section\n" + bank_entry("DE", "1", "COBADEFFXXX", "Commerzbank AG") + us_section)

    contents = build_clean_banks.build(catalogue, path)

    assert contents.endswith(us_section)
    assert "stale section" not in contents
    assert "commerzbank" not in contents.lower(), "every registry name containing the catalogue Bank's name goes"
    assert "ABBYGB2L" not in contents, "every registry entry sharing the catalogue Bank's BIC8 goes"
    assert build_clean_banks.build(catalogue, path) == contents, "the output is stable"
    for country in IBAN_COUNTRIES:
        assert f'country = "{country}"' in contents


def test_the_builder_refuses_a_file_without_the_us_marker(tmp_path: Path) -> None:
    path = tmp_path / "clean_banks.toml"
    path.write_text(US_ENTRY)

    with pytest.raises(ValueError, match="marker"):
        build_clean_banks.build(load_catalogue(), path)


def test_the_builder_spreads_its_pick_through_the_alphabet() -> None:
    assert build_clean_banks.spread(list(range(10)), 4) == [0, 2, 5, 7]
    assert build_clean_banks.spread([1, 2], 4) == [1, 2]
