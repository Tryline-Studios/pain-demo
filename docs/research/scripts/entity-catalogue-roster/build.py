# /// script
# requires-python = ">=3.13"
# ///
"""Collect roster facts from parsed list JSON (see parse_lists.py) and GLEIF.

Usage:
  python build.py collect   -> roster_data.json (list facts only)
  python build.py gleif     -> gleif.json (LEI records, BIC-to-LEI mapping hits)
  python build.py render    -> roster_detail.md (per-Entity detail + summary table rows)
"""

import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from roster import MANUAL_LEIS, ROSTER

B = Path(__file__).parent

UK_COUNTRY_ISO = {
    "Russia": "RU", "United Kingdom": "GB", "Iran": "IR", "North Korea": "KP", "Syria": "SY",
    "Belarus": "BY", "Venezuela": "VE", "Israel": "IL", "Portugal": "PT", "Germany": "DE",
    "Latvia": "LV", "Ukraine": "UA", "United States": "US", "Kazakhstan": "KZ", "China": "CN",
    "Cyprus": "CY", "United Arab Emirates": "AE", "Malaysia": "MY", "Turkey": "TR", "Lebanon": "LB",
    "Iraq": "IQ", "Netherlands": "NL", "Switzerland": "CH", "Singapore": "SG", "India": "IN",
}
OFAC_COUNTRY_ISO_EXTRA = {"Korea, North": "KP"}

ID_TYPES_KEEP = ("Registration Number", "Registration ID", "Tax ID No.", "Legal Entity Number", "Government Gazette Number", "Company Number", "Business Registration Number", "Commercial Registry Number", "Business Number")


def iso_date_uk(d):
    if not d:
        return None
    dd, mm, yy = d.split("/")
    return f"{yy}-{mm}-{dd}"


def infer_script(s):
    for ch in s:
        o = ord(ch)
        if 0x0400 <= o <= 0x04FF:
            return "Cyrillic"
        if 0x0600 <= o <= 0x06FF or 0xFB50 <= o <= 0xFEFF:
            return "Arabic"
        if 0x4E00 <= o <= 0x9FFF:
            return "Han"
        if 0xAC00 <= o <= 0xD7AF or 0x1100 <= o <= 0x11FF:
            return "Hangul"
    return None


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def collect():
    ofac_all = json.load(open(B / "ofac.json"))
    uk_all = json.load(open(B / "uk.json"))
    ofac, uk = ofac_all["parties"], uk_all["designations"]
    out = []
    for slug, etype, refs in ROSTER:
        e = {"id": slug, "entity_type": etype, "listings": [], "names": [], "non_latin": [], "addresses": [], "ids": [], "bics": [], "individual": {}, "uk_positions": [], "uk_other": [], "uk_sor": [], "ofac_titles": [], "ofac_relationships": [], "uk_entity_types": [], "uk_parent": [], "uk_subsidiaries": []}
        for lst, ref in refs:
            if lst == "OFAC":
                p = ofac[ref]
                sdn = [l for l in p["listings"] if l["list"] == "SDN List"]
                assert sdn, (slug, ref)
                progs = []
                for l in sdn:
                    for pr in l["programmes"]:
                        if pr not in progs:
                            progs.append(pr)
                dates = sorted({ev["date"] for l in sdn for ev in l["entry_events"] if ev["date"]})
                e["listings"].append({"list": "OFAC SDN", "entry_id": ref, "programmes": progs, "designation_date": dates[0] if dates else None, "party_type": p["party_type"]})
                for n in p["names"]:
                    if n["low_quality"]:
                        continue
                    nt = {"Name": "primary", "A.K.A.": "a.k.a.", "F.K.A.": "f.k.a.", "N.K.A.": "n.k.a."}[n["alias_type"]]
                    rec = {"value": clean(n["name"]), "name_type": nt, "script": n["script"], "language": None, "listing": f"OFAC {ref}"}
                    if n["script"] != "Latin":
                        e["non_latin"].append(rec)
                    else:
                        e["names"].append(rec)
                e["weak_excluded_ofac"] = [clean(n["name"]) for n in p["names"] if n["low_quality"]]
                for f in p["features"]:
                    t = f["type"]
                    if t == "SWIFT/BIC":
                        e["bics"].append({"bic": f["value"].strip(), "source": f"OFAC {ref}"})
                    elif t == "Location" and f.get("location"):
                        loc = f["location"]
                        e["addresses"].append({"source": f"OFAC {ref}", "lines": [loc.get(k) for k in ("ADDRESS1", "ADDRESS2", "ADDRESS3") if loc.get(k)], "city": loc.get("CITY"), "region": loc.get("STATE/PROVINCE"), "postcode": loc.get("POSTAL CODE"), "country": loc.get("COUNTRY"), "iso": loc.get("ISO")})
                    elif t == "Birthdate":
                        e["individual"].setdefault("dob", []).append((f.get("date") + (f" to {f['date_to']}" if f.get("date_to") else ""), f"OFAC {ref}"))
                    elif t == "Place of Birth":
                        e["individual"].setdefault("pob", []).append((f["value"], f"OFAC {ref}"))
                    elif t in ("Nationality Country", "Citizenship Country"):
                        c = (f.get("location") or {}).get("Unknown")
                        e["individual"].setdefault("nationality", []).append((f"{c} ({t.split()[0].lower()})", f"OFAC {ref}"))
                    elif t == "Title":
                        e["ofac_titles"].append(f["value"])
                    elif t in ("Organization Established Date",):
                        e.setdefault("established", []).append(f.get("date"))
                for d in p["id_docs"]:
                    if etype != "individual" and d["type"] in ID_TYPES_KEEP:
                        e["ids"].append({"type": d["type"], "value": d["number"], "country": d["country"], "source": f"OFAC {ref}"})
                for r in p["relationships"]:
                    e["ofac_relationships"].append(r)
            else:
                d = uk[ref]
                e["listings"].append({"list": "UK Sanctions List", "entry_id": ref, "programmes": [d["regime"]], "designation_date": iso_date_uk(d["date_designated"]), "last_updated": iso_date_uk(d["last_updated"]), "ofsi_group_id": d["ofsi_group_id"], "designation_source": d["source"], "un_ref": d["un_ref"]})
                for n in d["names"]:
                    v = clean(n["name"])
                    if not v:
                        continue
                    if (n["alias_strength"] or "").lower().startswith("low quality"):
                        e.setdefault("weak_excluded_uk", []).append(v)
                        continue
                    nt_raw = (n["name_type"] or "").lower()
                    nt = {"primary name": "primary", "primary name variation": "primary variation", "alias": "a.k.a."}.get(nt_raw, nt_raw)
                    e["names"].append({"value": v, "name_type": nt, "script": "Latin", "language": None, "listing": f"UK {ref}", "alias_strength": n["alias_strength"]})
                for n in d["non_latin"]:
                    v = clean(n["name"])
                    if not v:
                        continue
                    script = n["script"]
                    inferred = None
                    if not script:
                        inferred = infer_script(v)
                    e["non_latin"].append({"value": v, "name_type": "non-latin", "script": script or (f"{inferred} (inferred)" if inferred else None), "language": n["language"], "listing": f"UK {ref}"})
                for a in d["addresses"]:
                    lines = [clean(a.get(f"AddressLine{i}")) for i in range(1, 6) if a.get(f"AddressLine{i}")]
                    country = clean(a.get("AddressCountry")) or None
                    e["addresses"].append({"source": f"UK {ref}", "lines": lines, "city": clean(a.get("AddressLine6")) or None, "region": None, "postcode": clean(a.get("AddressPostalCode")) or None, "country": country, "iso": UK_COUNTRY_ISO.get(country) if country else None})
                for rn in d.get("registration_numbers") or []:
                    e["ids"].append({"type": "Business registration number", "value": clean(rn), "country": None, "source": f"UK {ref}"})
                e["uk_entity_types"] += d.get("entity_types") or []
                e["uk_parent"] += d.get("parent_companies") or []
                e["uk_subsidiaries"] += d.get("subsidiaries") or []
                if etype == "individual":
                    for dob in d.get("dobs") or []:
                        e["individual"].setdefault("dob", []).append((iso_date_uk(dob) if re.fullmatch(r"\d\d/\d\d/\d{4}", dob) else dob, f"UK {ref}"))
                    for b in d.get("birth") or []:
                        e["individual"].setdefault("pob", []).append((", ".join(x for x in (b["town"], b["country"]) if x), f"UK {ref}"))
                    for nat in d.get("nationalities") or []:
                        e["individual"].setdefault("nationality", []).append((nat, f"UK {ref}"))
                e["uk_positions"] += d.get("positions") or []
                if d.get("other_information"):
                    e["uk_other"].append(d["other_information"])
                if d.get("statement_of_reasons"):
                    e["uk_sor"].append(d["statement_of_reasons"])
        # residence proxy for individuals: countries of listed addresses (country only)
        if etype == "individual":
            e["individual"]["residence_countries"] = sorted({f"{a['country']} ({a['iso']})" for a in e["addresses"] if a["country"]} | set())
            e["individual"]["residence_sources"] = sorted({a["source"] for a in e["addresses"] if a["country"]})
            e["addresses"] = []  # never keep personal addresses
        out.append(e)
    meta = {"ofac_date_of_issue": ofac_all["date_of_issue"], "uk_date_generated": uk_all["date_generated"]}
    json.dump({"meta": meta, "entities": out}, open(B / "roster_data.json", "w"), ensure_ascii=False, indent=1)
    print("collected", len(out))


def http_json(url):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/vnd.api+json"}), timeout=60) as r:
                return json.load(r)
        except Exception as ex:  # noqa: BLE001
            print("retry", url, ex)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(url)


def gleif():
    data = json.load(open(B / "roster_data.json"))
    mapping_file = next(B.glob("lei-bic-*.csv"))
    lei_to_bics, bic_to_leis = {}, {}
    with open(mapping_file) as fh:
        for row in csv.DictReader(fh):
            lei_to_bics.setdefault(row["LEI"], []).append(row["BIC"])
            bic_to_leis.setdefault(row["BIC"][:8], set()).add(row["LEI"])
    cache = {}
    results = {}
    for e in data["entities"]:
        if e["entity_type"] == "individual":
            continue
        found = {}  # lei -> how found
        for i in e["ids"]:
            if i["type"] == "Legal Entity Number":
                found.setdefault(i["value"], []).append(f"{i['source']} Legal Entity Number")
        for b in e["bics"]:
            for lei in bic_to_leis.get(b["bic"][:8], ()):
                found.setdefault(lei, []).append(f"GLEIF BIC-to-LEI mapping ({mapping_file.name}) for {b['bic']}")
        regs = set()
        for i in e["ids"]:
            if i["type"] in ("Registration Number", "Registration ID", "Business registration number"):
                m = re.findall(r"\b\d{7,13}\b", i["value"])
                regs.update(m)
        for reg in sorted(regs):
            url = "https://api.gleif.org/api/v1/lei-records?" + urllib.parse.urlencode({"filter[entity.registeredAs]": reg, "page[size]": 10})
            js = http_json(url)
            time.sleep(1.1)
            for r in js["data"]:
                found.setdefault(r["id"], []).append(f"GLEIF lei-records filter[entity.registeredAs]={reg}")
        for lei, how in MANUAL_LEIS.get(e["id"], []):
            found.setdefault(lei, []).append(how)
        recs = {}
        for lei, how in found.items():
            if lei not in cache:
                js = http_json(f"https://api.gleif.org/api/v1/lei-records/{lei}")
                time.sleep(1.1)
                a = js["data"]["attributes"]
                cache[lei] = {
                    "lei": lei,
                    "legal_name": a["entity"]["legalName"]["name"],
                    "other_names": [n["name"] for n in a["entity"].get("otherNames") or []] + [n["name"] for n in a["entity"].get("transliteratedOtherNames") or []],
                    "country": a["entity"]["legalAddress"]["country"],
                    "registered_as": a["entity"].get("registeredAs"),
                    "entity_status": a["entity"]["status"],
                    "registration_status": a["registration"]["status"],
                    "last_update": a["registration"]["lastUpdateDate"],
                    "bic_attr": a.get("bic"),
                }
            recs[lei] = dict(cache[lei], found_via=how, mapping_bics=lei_to_bics.get(lei, []))
        results[e["id"]] = recs
        print(e["id"], list(recs))
    json.dump({"mapping_file": mapping_file.name, "results": results}, open(B / "gleif.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    {"collect": collect, "gleif": gleif}[sys.argv[1]]()
