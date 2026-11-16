# /// script
# requires-python = ">=3.13"
# dependencies = ["lxml"]
# ///
"""Parse OFAC SDN_ADVANCED.XML and the UK Sanctions List XML into JSON.

Usage: uv run parse_lists.py <dir-containing-downloads>

Writes ofac.json (keyed by OFAC UID / FixedRef) and uk.json (keyed by UK Unique ID).
Only SDN List (ListID 1550) SanctionsEntries are kept as Listings.
"""

import json
import sys
from pathlib import Path

from lxml import etree

NS = "{https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML}"


def q(tag: str) -> str:
    return NS + tag


def date_of(el) -> str | None:
    if el is None:
        return None
    y = el.findtext(q("Year"))
    m = el.findtext(q("Month"))
    d = el.findtext(q("Day"))
    parts = [p for p in (y, m, d) if p]
    if not parts:
        return None
    return "-".join([parts[0]] + [p.zfill(2) for p in parts[1:]])


def parse_ofac(path: Path) -> dict:
    tree = etree.parse(str(path))
    root = tree.getroot()
    doi = date_of(root.find(q("DateOfIssue")))
    rv = root.find(q("ReferenceValueSets"))

    def values(group: str, item: str, attr: str | None = None) -> dict:
        out = {}
        for e in rv.find(q(group)).findall(q(item)):
            out[e.get("ID")] = e.get(attr) if attr else (e.text or "")
        return out

    alias_types = values("AliasTypeValues", "AliasType")
    scripts = values("ScriptValues", "Script")
    feature_types = values("FeatureTypeValues", "FeatureType")
    detail_refs = values("DetailReferenceValues", "DetailReference")
    area_codes = values("AreaCodeValues", "AreaCode")
    countries = values("CountryValues", "Country")
    country_iso = {}
    for e in rv.find(q("AreaCodeValues")).findall(q("AreaCode")):
        country_iso[e.get("CountryID")] = e.text
    legal_bases = values("LegalBasisValues", "LegalBasis")
    lists = values("ListValues", "List")
    rel_types = values("RelationTypeValues", "RelationType")
    idreg_types = values("IDRegDocTypeValues", "IDRegDocType")
    loc_part_types = values("LocPartTypeValues", "LocPartType")
    party_subtypes = {}
    for e in rv.find(q("PartySubTypeValues")).findall(q("PartySubType")):
        party_subtypes[e.get("ID")] = e.get("PartyTypeID")
    party_types = values("PartyTypeValues", "PartyType")

    locations = {}
    for loc in root.find(q("Locations")).findall(q("Location")):
        parts = {}
        for lp in loc.findall(q("LocationPart")):
            t = loc_part_types.get(lp.get("LocPartTypeID"), lp.get("LocPartTypeID"))
            v = lp.findtext(f"{q('LocationPartValue')}/{q('Value')}")
            parts[t] = v
        c = loc.find(q("LocationCountry"))
        if c is not None:
            parts["COUNTRY"] = countries.get(c.get("CountryID"))
            parts["ISO"] = country_iso.get(c.get("CountryID"))
        locations[loc.get("ID")] = parts

    parties: dict[str, dict] = {}
    profile_to_uid: dict[str, str] = {}
    identity_to_uid: dict[str, str] = {}
    for dp in root.find(q("DistinctParties")).findall(q("DistinctParty")):
        uid = dp.get("FixedRef")
        prof = dp.find(q("Profile"))
        profile_to_uid[prof.get("ID")] = uid
        ptype = party_types.get(party_subtypes.get(prof.get("PartySubTypeID")))
        names = []
        for ident in prof.findall(q("Identity")):
            identity_to_uid[ident.get("ID")] = uid
            for al in ident.findall(q("Alias")):
                for dn in al.findall(q("DocumentedName")):
                    vals = dn.findall(f"{q('DocumentedNamePart')}/{q('NamePartValue')}")
                    text = " ".join((v.text or "") for v in vals)
                    script = scripts.get(vals[0].get("ScriptID")) if vals else None
                    names.append(
                        {
                            "name": text,
                            "alias_type": alias_types.get(al.get("AliasTypeID")),
                            "primary": al.get("Primary") == "true",
                            "low_quality": al.get("LowQuality") == "true",
                            "script": script,
                            "doc_name_id": dn.get("ID"),
                        }
                    )
        features = []
        for f in prof.findall(q("Feature")):
            ft = feature_types.get(f.get("FeatureTypeID"))
            for fv in f.findall(q("FeatureVersion")):
                item = {"type": ft}
                vd = fv.find(q("VersionDetail"))
                if vd is not None:
                    if vd.get("DetailReferenceID"):
                        item["value"] = detail_refs.get(vd.get("DetailReferenceID"))
                    else:
                        item["value"] = vd.text
                dp_ = fv.find(q("DatePeriod"))
                if dp_ is not None:
                    item["date"] = date_of(dp_.find(f"{q('Start')}/{q('From')}"))
                    to = date_of(dp_.find(f"{q('End')}/{q('To')}"))
                    if to and to != item["date"]:
                        item["date_to"] = to
                vl = fv.find(q("VersionLocation"))
                if vl is not None:
                    item["location"] = locations.get(vl.get("LocationID"))
                features.append(item)
        parties[uid] = {
            "uid": uid,
            "party_type": ptype,
            "names": names,
            "features": features,
            "id_docs": [],
            "listings": [],
            "relationships": [],
        }

    for doc in root.find(q("IDRegDocuments")).findall(q("IDRegDocument")):
        uid = identity_to_uid.get(doc.get("IdentityID"))
        if uid is None:
            continue
        parties[uid]["id_docs"].append(
            {
                "type": idreg_types.get(doc.get("IDRegDocTypeID")),
                "number": doc.findtext(q("IDRegistrationNo")),
                "country": countries.get(doc.get("IssuedBy-CountryID")),
            }
        )

    for rel in root.find(q("ProfileRelationships")).findall(q("ProfileRelationship")):
        fr = profile_to_uid.get(rel.get("From-ProfileID"))
        to = profile_to_uid.get(rel.get("To-ProfileID"))
        item = {
            "from": fr,
            "to": to,
            "type": rel_types.get(rel.get("RelationTypeID")),
            "former": rel.get("Former") == "true",
        }
        if fr in parties:
            parties[fr]["relationships"].append(item)
        if to in parties and to != fr:
            parties[to]["relationships"].append(item)

    for se in root.find(q("SanctionsEntries")).findall(q("SanctionsEntry")):
        uid = profile_to_uid.get(se.get("ProfileID"))
        if uid is None:
            continue
        ev = se.findall(q("EntryEvent"))
        programmes = [
            m.findtext(q("Comment"))
            for m in se.findall(q("SanctionsMeasure"))
            if m.get("SanctionsTypeID") == "1"
        ]
        parties[uid]["listings"].append(
            {
                "list": lists.get(se.get("ListID")),
                "entry_events": [
                    {
                        "date": date_of(e.find(q("Date"))),
                        "legal_basis": legal_bases.get(e.get("LegalBasisID")),
                    }
                    for e in ev
                ],
                "programmes": programmes,
            }
        )

    # name of related parties for convenience
    for p in parties.values():
        for r in p["relationships"]:
            for k in ("from", "to"):
                other = parties.get(r[k])
                if other:
                    prim = next((n["name"] for n in other["names"] if n["primary"] and n["script"] == "Latin"), None)
                    r[k + "_name"] = prim
    return {"date_of_issue": doi, "parties": parties}


def text(el, tag):
    v = el.findtext(tag)
    return v.strip() if v else None


def parse_uk(path: Path) -> dict:
    root = etree.parse(str(path)).getroot()
    out = {}
    for d in root.findall("Designation"):
        uid = text(d, "UniqueID")
        names = []
        for n in d.findall("Names/Name"):
            parts = [text(n, f"Name{i}") for i in range(1, 7)]
            names.append(
                {
                    "name": " ".join(p for p in parts if p),
                    "name_type": text(n, "NameType"),
                    "alias_strength": text(n, "AliasStrength"),
                }
            )
        nonlatin = [
            {
                "name": text(n, "NameNonLatinScript"),
                "script": text(n, "NonLatinScriptType"),
                "language": text(n, "NonLatinScriptLanguage"),
            }
            for n in d.findall("NonLatinNames/NonLatinName")
        ]
        addresses = []
        for a in d.findall("Addresses/Address"):
            addr = {c.tag: (c.text or "").strip() for c in a}
            addresses.append(addr)
        rec = {
            "unique_id": uid,
            "ofsi_group_id": text(d, "OFSIGroupID"),
            "un_ref": text(d, "UNReferenceNumber"),
            "date_designated": text(d, "DateDesignated"),
            "last_updated": text(d, "LastUpdated"),
            "regime": text(d, "RegimeName"),
            "type": text(d, "IndividualEntityShip"),
            "source": text(d, "DesignationSource"),
            "sanctions_imposed": text(d, "SanctionsImposed"),
            "other_information": text(d, "OtherInformation"),
            "statement_of_reasons": text(d, "UKStatementofReasons"),
            "names": names,
            "non_latin": nonlatin,
            "addresses": addresses,
            "websites": [(w.text or "").strip() for w in d.findall("Websites/Website")],
        }
        ent = d.find("EntityDetails/Entity")
        if ent is not None:
            rec["entity_types"] = [(t.text or "").strip() for t in ent.findall("TypeOfEntities/TypeOfEntity")]
            rec["registration_numbers"] = [
                (t.text or "").strip() for t in ent.findall("BusinessRegistrationNumbers/BusinessRegistrationNumber")
            ]
            rec["parent_companies"] = [(t.text or "").strip() for t in ent.findall("ParentCompanies/ParentCompany")]
            rec["subsidiaries"] = [(t.text or "").strip() for t in ent.findall("Subsidiaries/Subsidiary")]
        ind = d.find("IndividualDetails/Individual")
        if ind is not None:
            rec["dobs"] = [(t.text or "").strip() for t in ind.findall("DOBs/DOB")]
            rec["nationalities"] = [(t.text or "").strip() for t in ind.findall("Nationalities/Nationality")]
            rec["positions"] = [(t.text or "").strip() for t in ind.findall("Positions/Position")]
            rec["birth"] = [
                {"town": text(loc, "TownOfBirth"), "country": text(loc, "CountryOfBirth")}
                for loc in ind.findall("BirthDetails/Location")
            ]
        out[uid] = rec
    return {"date_generated": root.findtext("DateGenerated"), "designations": out}


def main() -> None:
    base = Path(sys.argv[1])
    ofac = parse_ofac(base / "SDN_ADVANCED.XML")
    (base / "ofac.json").write_text(json.dumps(ofac, ensure_ascii=False, indent=1))
    uk = parse_uk(base / "UK-Sanctions-List.xml")
    (base / "uk.json").write_text(json.dumps(uk, ensure_ascii=False, indent=1))
    print("OFAC date of issue", ofac["date_of_issue"], len(ofac["parties"]))
    print("UK date generated", uk["date_generated"], len(uk["designations"]))


if __name__ == "__main__":
    main()
