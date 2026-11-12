"""`just verify-catalogue` and `just verify-clean-banks` (spec 3.4, 4.3) against small extracts of the lists."""

from pathlib import Path

import pytest

from pain_demo import freshness

FIXTURES = Path(__file__).parent / "freshness"


def fake_fetch(url: str) -> bytes:
    """Serve the fixture extract for each list URL; the tests never touch the network."""
    files = {freshness.OFAC_URL: "SDN_ADVANCED.XML", freshness.UK_URL: "UK-Sanctions-List.xml"}
    return (FIXTURES / files[url]).read_bytes()


SBERBANK = """
id = "sberbank"
entity_type = "bank"

[[listings]]
list = "ofac_sdn"
entry_id = "{ofac_uid}"
programmes = ["RUSSIA-EO14024"]
designation_date = 2022-04-06
verified = {{ snapshot_date = 2026-09-14, source_file = "SDN_ADVANCED.XML" }}

[[listings]]
list = "uk"
entry_id = "RUS0256"
programmes = ["The Russia (Sanctions) (EU Exit) Regulations 2019"]
designation_date = 2022-03-01
verified = {{ snapshot_date = 2026-09-11, source_file = "UK-Sanctions-List.xml" }}

[[names]]
value = "{ofac_name}"
source_type = "primary"
script = "latin"
script_source = "stated"
listing = {{ list = "ofac_sdn", entry_id = "{ofac_uid}" }}

[[names]]
value = "ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО СБЕРБАНК РОССИИ"
source_type = "primary"
script = "cyrillic"
script_source = "stated"
listing = {{ list = "ofac_sdn", entry_id = "{ofac_uid}" }}

[[names]]
value = "PJSC Sberbank (Public Joint-Stock Company Sberbank)"
source_type = "primary"
script = "latin"
script_source = "derived"
listing = {{ list = "uk", entry_id = "RUS0256" }}

[[names]]
value = "PJSC Sberbank of Russia"
source_type = "primary_variation"
script = "latin"
script_source = "derived"
listing = {{ list = "uk", entry_id = "RUS0256" }}

[[names]]
value = "ПАО Сбербанк"
source_type = "aka"
script = "cyrillic"
script_source = "derived"
listing = {{ list = "uk", entry_id = "RUS0256" }}

[[bics]]
value = "{bic}"
listing = {{ list = "ofac_sdn", entry_id = "{ofac_uid}" }}
verified_date = 2026-09-14

[[bics]]
value = "SABRINDDXXX"
citation = "GLEIF BIC-to-LEI mapping, which the lists do not carry"
verified_date = 2026-08-28
"""


def catalogue_root(
    tmp_path: Path,
    ofac_uid: str = "17018",
    ofac_name: str = "PUBLIC JOINT STOCK COMPANY SBERBANK OF RUSSIA",
    bic: str = "SABRRUMM",
) -> Path:
    root = tmp_path / "catalogue"
    (root / "entities").mkdir(parents=True)
    entity = SBERBANK.format(ofac_uid=ofac_uid, ofac_name=ofac_name, bic=bic)
    (root / "entities" / "sberbank.toml").write_text(entity, encoding="utf-8")
    (root / "control_relationships.toml").write_text("", encoding="utf-8")
    return root


def verify_catalogue(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = freshness.main(["catalogue", "--catalogue-root", str(root)], fetch=fake_fetch)
    return code, capsys.readouterr().out


# --- just verify-catalogue


def test_a_catalogue_matching_both_lists_reports_no_drift_with_the_snapshot_dates(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = verify_catalogue(catalogue_root(tmp_path), capsys)

    assert code == 0
    assert "OFAC SDN_ADVANCED.XML issued 2026-11-09" in out
    assert "UK Sanctions List generated 2026-11-12" in out
    assert "no drift" in out


@pytest.mark.parametrize(
    ("catalogue", "drift"),
    [
        ({"ofac_uid": "99999"}, "sberbank: ofac_sdn 99999 delisted"),
        ({"ofac_uid": "36"}, "sberbank: ofac_sdn 36 delisted"),  # UID 36 is on a non-SDN list only
        (
            {"ofac_name": "SBERBANK PJSC"},
            "sberbank: ofac_sdn 17018 renamed: 'SBERBANK PJSC' is no longer on the Listing",
        ),
        ({"bic": "SABRRUM2"}, "sberbank: ofac_sdn 17018 BIC changed: catalogue ['SABRRUM2'], list ['SABRRUMM']"),
    ],
)
def test_drift_is_reported_and_exits_non_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], catalogue: dict[str, str], drift: str
) -> None:
    code, out = verify_catalogue(catalogue_root(tmp_path, **catalogue), capsys)

    assert code == 1
    assert drift in out
    assert "no drift" not in out


def test_a_bic11_on_the_catalogue_matches_its_bic8_on_the_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = verify_catalogue(catalogue_root(tmp_path, bic="SABRRUMMXXX"), capsys)

    assert (code, "no drift" in out) == (0, True)


def test_a_uk_list_whose_date_cannot_be_parsed_says_so_with_its_own_exit_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def fetch(url: str) -> bytes:
        return fake_fetch(url).replace(b"12/11/2026", b"2026-11-12T08:00:00")

    code = freshness.main(["catalogue", "--catalogue-root", str(catalogue_root(tmp_path))], fetch=fetch)

    assert code == freshness.UNREADABLE_LIST
    assert code != freshness.FOUND
    assert "could not parse the UK Sanctions List DateGenerated '2026-11-12T08:00:00'" in capsys.readouterr().err


@pytest.mark.parametrize(
    "ofac_name",
    [
        "Public  Joint Stock Company Sberbank of Russia",
        # the UK file has names like "(金铁三)" and "بانک ملی ایران, " that the catalogue stores without the stray marks
        "(PUBLIC JOINT STOCK COMPANY SBERBANK OF RUSSIA), ",
    ],
)
def test_names_compare_ignoring_case_spacing_and_surrounding_punctuation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], ofac_name: str
) -> None:
    root = catalogue_root(tmp_path, ofac_name=ofac_name)

    code, _ = verify_catalogue(root, capsys)

    assert code == 0


# --- just verify-clean-banks

US_ENTRY = """
[[banks]]
country = "US"
bank_code = "021000021"
bic = "CHASUS33"
name = "JPMorgan Chase Bank, N.A."
routing_number = "021000021"
"""


def verify_clean_banks(tmp_path: Path, capsys: pytest.CaptureFixture[str], *entries: str) -> tuple[int, str]:
    path = tmp_path / "clean_banks.toml"
    path.write_text(US_ENTRY + "".join(entries), encoding="utf-8")
    argv = ["clean-banks", "--catalogue-root", str(catalogue_root(tmp_path)), "--clean-banks", str(path)]
    code = freshness.main(argv, fetch=fake_fetch)
    return code, capsys.readouterr().out


def bank_entry(country: str, bic: str, name: str) -> str:
    return f'\n[[banks]]\ncountry = "{country}"\nbank_code = "1"\nbic = "{bic}"\nname = "{name}"\n'


def test_a_clean_list_reports_no_matches(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out = verify_clean_banks(tmp_path, capsys, bank_entry("DE", "COBADEFFXXX", "Commerzbank AG"))

    assert code == 0
    assert "OFAC SDN_ADVANCED.XML issued 2026-11-09" in out
    assert "no Clean Bank List entry matches either list" in out


@pytest.mark.parametrize(
    ("entry", "match"),
    [
        (bank_entry("DE", "COBADEFFXXX", "Sberbank of Russia"), "matches OFAC 17018 by name"),
        (bank_entry("DE", "COBADEFFXXX", "Sberbank-Europe AG"), "matches OFAC 18716 by name"),
        (bank_entry("GB", "BARCGB22XXX", "SBERBANK"), "GB BARCGB22XXX 'SBERBANK' matches UK RUS0256 by name"),
        (bank_entry("AT", "SABRATWWXXX", "Some Bank AG"), "AT SABRATWWXXX 'Some Bank AG' matches OFAC 18716 by BIC"),
    ],
)
def test_an_entry_on_either_list_is_reported_and_exits_non_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], entry: str, match: str
) -> None:
    code, out = verify_clean_banks(tmp_path, capsys, entry)

    assert code == 1
    assert match in out


def test_a_non_sdn_entry_is_not_a_match(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, _ = verify_clean_banks(tmp_path, capsys, bank_entry("DE", "COBADEFFXXX", "Aerocaribbean Airlines"))

    assert code == 0
