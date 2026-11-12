"""`just verify-catalogue` and `just verify-clean-banks`: check our frozen data against the live lists (spec 3.4, 4.3).

Both download the current OFAC `SDN_ADVANCED.XML` and UK Sanctions List XML, report, and exit 1 when they find
something, so they can be scripted. Neither writes anything: a human edits the catalogue or the Clean Bank List from
the report, regenerates the goldens and bumps the minor version (spec 15.4). They run by hand, never in CI.

- `catalogue`: each catalogue Listing is looked up by OFAC UID (SDN List entries only) or UK Unique ID. It is
  *delisted* when the entry is gone, *renamed* when a name the catalogue takes from it is no longer on it, and *BIC
  changed* when the BICs the catalogue takes from an OFAC Listing differ from the entry's `SWIFT/BIC` features.
- `clean-banks`: each Clean Bank List entry matches when its normalised name equals any name on either list, or its
  BIC8 equals the BIC8 of any OFAC `SWIFT/BIC` (the UK list has no BIC field).
"""

import argparse
import io
import re
import unicodedata
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from lxml import etree

from pain_demo.catalogue import DEFAULT_ROOT, Catalogue, load_catalogue
from pain_demo.generation import clean_banks
from pain_demo.identifiers import bic8

OFAC_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.XML"
UK_URL = "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml"

_OFAC_NS = "{https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML}"


@dataclass
class ListEntry:
    names: list[str] = field(default_factory=list)
    bics: list[str] = field(default_factory=list)


@dataclass
class SanctionsFile:
    """One downloaded list: when it was issued and its entries by OFAC UID or UK Unique ID."""

    label: str
    issued: str
    entries: dict[str, ListEntry]


def parse_ofac(source: bytes) -> SanctionsFile:
    """The SDN List entries of `SDN_ADVANCED.XML`, streamed: the file is over 100 MB."""
    issued = ""
    bic_feature_types: set[str] = set()
    sdn_list_ids: set[str] = set()
    parties: dict[str, ListEntry] = {}
    on_sdn: set[str] = set()
    for _, element in etree.iterparse(io.BytesIO(source), tag=f"{_OFAC_NS}*"):
        tag = etree.QName(element).localname
        if tag == "DateOfIssue":
            issued = "-".join(element.findtext(_OFAC_NS + part, "").zfill(2) for part in ("Year", "Month", "Day"))
        elif tag == "FeatureType" and element.text == "SWIFT/BIC":
            bic_feature_types.add(element.get("ID", ""))
        elif tag == "List" and element.text == "SDN List":
            sdn_list_ids.add(element.get("ID", ""))
        elif tag == "DistinctParty":
            parties[element.get("FixedRef", "")] = _ofac_party(element, bic_feature_types)
            element.clear()
        elif tag == "SanctionsEntry":
            if element.get("ListID") in sdn_list_ids:
                on_sdn.add(element.get("ProfileID", ""))
            element.clear()
    entries = {uid: entry for uid, entry in parties.items() if uid in on_sdn}
    return SanctionsFile("OFAC SDN_ADVANCED.XML issued", issued, entries)


def _ofac_party(party: etree._Element, bic_feature_types: set[str]) -> ListEntry:
    names = [
        " ".join(part.text or "" for part in name.iter(f"{_OFAC_NS}NamePartValue"))
        for name in party.iter(f"{_OFAC_NS}DocumentedName")
    ]
    bics = [
        (detail.text or "").strip()
        for feature in party.iter(f"{_OFAC_NS}Feature")
        if feature.get("FeatureTypeID") in bic_feature_types
        for detail in feature.iter(f"{_OFAC_NS}VersionDetail")
    ]
    return ListEntry(names=names, bics=bics)


def parse_uk(source: bytes) -> SanctionsFile:
    root = etree.fromstring(source)
    generated = datetime.strptime(root.findtext("DateGenerated", "").strip(), "%d/%m/%Y").date().isoformat()
    entries: dict[str, ListEntry] = {}
    for designation in root.iter("Designation"):
        names = [
            " ".join(part for index in range(1, 7) if (part := name.findtext(f"Name{index}", "")))
            for name in designation.iterfind("Names/Name")
        ]
        names += [name.text or "" for name in designation.iterfind("NonLatinNames/NonLatinName/NameNonLatinScript")]
        entries[designation.findtext("UniqueID", "").strip()] = ListEntry(names=names)
    return SanctionsFile("UK Sanctions List generated", generated, entries)


def name_key(name: str) -> str:
    """How a catalogue name is compared with a list name: any script; case, spacing and stray end marks ignored."""
    return " ".join(re.sub(r"^\W+|\W+$", "", unicodedata.normalize("NFKC", name).casefold()).split())


def catalogue_drift(catalogue: Catalogue, ofac: SanctionsFile, uk: SanctionsFile) -> Iterator[str]:
    files = {"ofac_sdn": ofac, "uk": uk}
    for entity in sorted(catalogue.entities.values(), key=lambda entity: entity.id):
        for listing in entity.listings:
            where = f"{entity.id}: {listing.list} {listing.entry_id}"
            entry = files[listing.list].entries.get(listing.entry_id)
            if entry is None:
                yield f"{where} delisted (not on the list)"
                continue
            on_list = {name_key(name) for name in entry.names}
            for name in entity.names:
                if name.listing == listing.ref and name_key(name.value) not in on_list:
                    yield f"{where} renamed: {name.value!r} is no longer on the Listing"
            if listing.list == "ofac_sdn":
                ours = sorted(bic.value for bic in getattr(entity, "bics", []) if bic.listing == listing.ref)
                theirs = sorted(entry.bics)
                if ours != theirs:
                    yield f"{where} BIC changed: catalogue {ours}, list {theirs}"


def clean_bank_matches(banks: clean_banks.CleanBankList, ofac: SanctionsFile, uk: SanctionsFile) -> Iterator[str]:
    names: dict[str, str] = {}
    bic8s: dict[str, str] = {}
    for file, prefix in ((ofac, "OFAC"), (uk, "UK")):
        for entry_id, entry in file.entries.items():
            for name in entry.names:
                if normalised := clean_banks.normalise_name(name):
                    names.setdefault(normalised, f"{prefix} {entry_id}")
            for bic in entry.bics:
                bic8s.setdefault(bic8(bic), f"{prefix} {entry_id}")
    for bank in banks.banks:
        where = f"{bank.country} {bank.bic} {bank.name!r}"
        if (listing := names.get(clean_banks.normalise_name(bank.name))) is not None:
            yield f"{where} matches {listing} by name"
        if (listing := bic8s.get(bic8(bank.bic))) is not None:
            yield f"{where} matches {listing} by BIC"


def download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=300) as response:  # noqa: S310 - fixed https URLs
        return response.read()


def main(argv: list[str] | None = None, fetch: Callable[[str], bytes] = download) -> int:
    parser = argparse.ArgumentParser(prog="python -m pain_demo.freshness", description=__doc__.splitlines()[0])
    parser.add_argument("check", choices=["catalogue", "clean-banks"])
    parser.add_argument("--catalogue-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--clean-banks", type=Path, default=clean_banks.DEFAULT_PATH)
    args = parser.parse_args(argv)

    catalogue = load_catalogue(args.catalogue_root)
    ofac, uk = parse_ofac(fetch(OFAC_URL)), parse_uk(fetch(UK_URL))
    for file in (ofac, uk):
        print(f"{file.label} {file.issued}: {len(file.entries)} entries")
    if args.check == "catalogue":
        found, nothing = list(catalogue_drift(catalogue, ofac, uk)), "no drift"
    else:
        banks = clean_banks.load_clean_banks(catalogue, args.clean_banks)
        found, nothing = list(clean_bank_matches(banks, ofac, uk)), "no Clean Bank List entry matches either list"
    print("\n".join(found) or nothing)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
