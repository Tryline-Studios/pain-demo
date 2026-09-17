"""The Entity Catalogue: schema, loading and startup validation (spec section 3)."""

import json
from datetime import date
from pathlib import Path

import pytest

from pain_demo.app import create_app
from pain_demo.catalogue import CatalogueError, load_catalogue
from pain_demo.settings import Settings


def test_the_shipped_catalogue_holds_the_full_roster(roster_ids: list[str]) -> None:
    catalogue = load_catalogue()

    assert list(catalogue.entities) == roster_ids
    assert len(catalogue.entities) == 50
    assert catalogue.snapshot_date == date(2026, 9, 14)


MINIMAL_BANK = """
id = "test-bank"
entity_type = "bank"

[[listings]]
list = "ofac_sdn"
entry_id = "1"
programmes = ["RUSSIA-EO14024"]
designation_date = 2022-04-06
verified = { snapshot_date = 2026-09-14, source_file = "SDN_ADVANCED.XML" }

[[names]]
value = "TEST BANK"
source_type = "primary"
script = "latin"
script_source = "stated"
listing = { list = "ofac_sdn", entry_id = "1" }
"""

MINIMAL_INDIVIDUAL = """
id = "test-individual"
entity_type = "individual"

[[listings]]
list = "uk"
entry_id = "RUS0001"
programmes = ["The Russia (Sanctions) (EU Exit) Regulations 2019"]
designation_date = 2022-03-10
verified = { snapshot_date = 2026-09-11, source_file = "UK-Sanctions-List.xml" }

[[names]]
value = "Test INDIVIDUAL"
source_type = "primary"
script = "latin"
script_source = "derived"
listing = { list = "uk", entry_id = "RUS0001" }
"""


def write_catalogue(root: Path, entities: dict[str, str], relationships: str = "") -> Path:
    (root / "entities").mkdir()
    for entity_id, toml in entities.items():
        (root / "entities" / f"{entity_id}.toml").write_text(toml, encoding="utf-8")
    (root / "control_relationships.toml").write_text(relationships, encoding="utf-8")
    return root


def problems_of(root: Path) -> list[str]:
    with pytest.raises(CatalogueError) as raised:
        load_catalogue(root)
    return raised.value.problems


def test_a_minimal_catalogue_loads_and_a_bank_may_have_no_bic(tmp_path: Path) -> None:
    catalogue = load_catalogue(write_catalogue(tmp_path, {"test-bank": MINIMAL_BANK}))

    bank = catalogue.entities["test-bank"]
    assert bank.entity_type == "bank"
    assert bank.bics == []
    assert bank.display_name == "TEST BANK"


def test_an_id_must_match_its_filename(tmp_path: Path) -> None:
    problems = problems_of(write_catalogue(tmp_path, {"other-name": MINIMAL_BANK}))

    assert problems == ["other-name.toml: id 'test-bank' does not match the filename"]


def test_ids_must_be_unique(tmp_path: Path) -> None:
    root = write_catalogue(tmp_path, {"test-bank": MINIMAL_BANK, "test-bank-2": MINIMAL_BANK})

    assert any(problem.endswith("duplicate id 'test-bank'") for problem in problems_of(root))


def test_an_entity_needs_at_least_one_listing(tmp_path: Path) -> None:
    no_listings = MINIMAL_BANK.replace("[[listings]]", "[[unrelated]]")

    problems = problems_of(write_catalogue(tmp_path, {"test-bank": no_listings}))

    assert any("listings" in problem for problem in problems)


def test_a_name_must_come_from_one_of_the_entitys_own_listings(tmp_path: Path) -> None:
    foreign_name = (
        MINIMAL_BANK
        + """
[[names]]
value = "Test Bank Rossii"
source_type = "aka"
script = "latin"
script_source = "stated"
listing = { list = "uk", entry_id = "RUS9999" }
"""
    )

    problems = problems_of(write_catalogue(tmp_path, {"test-bank": foreign_name}))

    assert problems == ["test-bank.toml: bank: Value error, uk RUS9999 is not one of this Entity's Listings"]


def test_weak_aliases_cannot_be_recorded(tmp_path: Path) -> None:
    weak = (
        MINIMAL_BANK
        + """
[[names]]
value = "TB"
source_type = "aka"
script = "latin"
script_source = "stated"
strength = "weak"
listing = { list = "ofac_sdn", entry_id = "1" }
"""
    )

    problems = problems_of(write_catalogue(tmp_path, {"test-bank": weak}))

    assert problems == ["test-bank.toml: bank.names.1.strength: Extra inputs are not permitted"]


def test_an_individual_carries_no_addresses_or_identifiers(tmp_path: Path) -> None:
    with_address = (
        MINIMAL_INDIVIDUAL
        + """
[[addresses]]
lines = ["1 Home Street"]
country = "RU"
listing = { list = "uk", entry_id = "RUS0001" }
"""
    )

    problems = problems_of(write_catalogue(tmp_path, {"test-individual": with_address}))

    assert problems == ["test-individual.toml: individual.addresses: Extra inputs are not permitted"]


@pytest.mark.parametrize("bic", ["SABRRUM", "sabrrumm", "SABRRUMMX", "SABRZZMM"])
def test_a_bic_must_be_well_formed(tmp_path: Path, bic: str) -> None:
    bad_bic = (
        MINIMAL_BANK
        + f"""
[[bics]]
value = "{bic}"
listing = {{ list = "ofac_sdn", entry_id = "1" }}
verified_date = 2026-09-14
"""
    )

    problems = problems_of(write_catalogue(tmp_path, {"test-bank": bad_bic}))

    assert len(problems) == 1
    assert problems[0].startswith("test-bank.toml: bank.bics.0.value: ")


def test_a_bic_names_exactly_one_source(tmp_path: Path) -> None:
    two_sources = (
        MINIMAL_BANK
        + """
[[bics]]
value = "SABRRUMM"
listing = { list = "ofac_sdn", entry_id = "1" }
citation = "GLEIF BIC-to-LEI mapping"
verified_date = 2026-09-14
"""
    )

    problems = problems_of(write_catalogue(tmp_path, {"test-bank": two_sources}))

    assert problems == [
        "test-bank.toml: bank.bics.0: Value error, a BIC names exactly one source: its Listing or an external citation",
    ]


@pytest.mark.parametrize("lei", ["549300WE6TAF5EEWQS8", "549300WE6TAF5EEWQS82", "549300we6taf5eewqs81"])
def test_an_lei_must_be_well_formed(tmp_path: Path, lei: str) -> None:
    bad_lei = (
        MINIMAL_BANK
        + f"""
[lei]
value = "{lei}"
gleif_legal_name = "TEST BANK"
source = "GLEIF lei-records on 2026-09-16"
"""
    )

    problems = problems_of(write_catalogue(tmp_path, {"test-bank": bad_lei}))

    assert len(problems) == 1
    assert problems[0].startswith("test-bank.toml: bank.lei.value: ")


def test_a_relationship_must_reference_catalogue_entities(tmp_path: Path) -> None:
    root = write_catalogue(
        tmp_path,
        {"test-bank": MINIMAL_BANK},
        """
[[relationships]]
controller = "nobody"
controlled = "test-bank"
role = "director"
status = "current"
as_of = 2025-04-09
source = "UK RUS0001 position"
""",
    )

    assert problems_of(root) == [
        "control_relationships.toml: nobody -> test-bank: controller 'nobody' is not in the catalogue",
    ]


def test_a_relationship_controls_a_legal_entity(tmp_path: Path) -> None:
    root = write_catalogue(
        tmp_path,
        {"test-bank": MINIMAL_BANK, "test-individual": MINIMAL_INDIVIDUAL},
        """
[[relationships]]
controller = "test-bank"
controlled = "test-individual"
role = "parent_company"
status = "current"
as_of = 2025-04-09
source = "made up"
""",
    )

    assert problems_of(root) == [
        "control_relationships.toml: test-bank -> test-individual: "
        "the controlled Entity must be a Legal Entity, not an Individual",
    ]


def test_every_problem_is_reported_at_once(tmp_path: Path) -> None:
    root = write_catalogue(tmp_path, {"wrong-name": MINIMAL_BANK, "broken": "id = [unterminated"})

    problems = problems_of(root)

    assert len(problems) == 2
    assert problems[0].startswith("broken.toml: ")
    assert problems[1] == "wrong-name.toml: id 'test-bank' does not match the filename"


def test_a_malformed_catalogue_logs_critical_and_exits_non_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = write_catalogue(tmp_path, {"wrong-name": MINIMAL_BANK})

    with pytest.raises(SystemExit) as raised:
        create_app(Settings(log_format="json"), catalogue_root=root)

    assert raised.value.code == 1
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(events) == 1
    (event,) = events
    assert event["level"] == "critical"
    assert event["event"] == "catalogue_invalid"
    assert event["problems"] == ["wrong-name.toml: id 'test-bank' does not match the filename"]
