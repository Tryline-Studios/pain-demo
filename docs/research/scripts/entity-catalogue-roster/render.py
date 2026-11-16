"""Render the summary table and per-Entity detail sections from roster_data.json + gleif.json."""

import json
from collections import Counter

D = json.load(open("roster_data.json"))
G = json.load(open("gleif.json"))
ENT = D["entities"]

GROUP_OVERRIDE = {"dandong-hongxiang": ["DPRK"], "mahan-air": ["Iran"], "vtb-bank": ["Russia"], "evrofinance-mosnarbank": ["Russia", "Venezuela"]}

REL = {  # slug -> short relationship label for the summary table (details in the Control Relationships section)
    "roman-abramovich": "UBO of `evraz-plc` (current)",
    "alexander-abramov": "director of `evraz-plc` (former); UBO of `evraz-plc` (current)",
    "andrey-kostin": "director of `vtb-bank` (current)",
    "herman-gref": "director of `sberbank` (current)",
    "andrey-akimov": "director of `gazprombank` (current)",
    "mikhail-fridman": "director of `alfa-bank` (former)",
    "yuri-kovalchuk": "controlling shareholder + director of `bank-rossiya` (current)",
    "igor-sechin": "director of `rosneft` (current)",
    "sergey-chemezov": "director of `rostec` (current)",
    "rami-makhlouf": "UBO of `syriatel` (current)",
    "fares-chehabi": "director of `cham-holding` (current)",
    "ahmad-derakhshandeh": "director of `bank-sepah` (former)",
    "simon-zerpa": "director of `bandes` (status not stated) ⚠",
    "kim-chol-sam": "treasurer/representative of `daedong-credit-bank` (role not in schema) ⚠",
    "sberbank": "parent of `sberbank-europe`",
    "sberbank-europe": "subsidiary of `sberbank`",
    "evraz-plc": "parent of `evraz-ntmk`",
    "evraz-ntmk": "subsidiary of `evraz-plc`",
}


def groups(e):
    if e["id"] in GROUP_OVERRIDE:
        return GROUP_OVERRIDE[e["id"]]
    g = []
    for l in e["listings"]:
        for p in l["programmes"]:
            for key, name in (("RUSSIA", "Russia"), ("UKRAINE", "Russia"), ("Russia", "Russia"), ("IRAN", "Iran"), ("IFSR", "Iran"), ("Iran", "Iran"), ("DPRK", "DPRK"), ("Korea", "DPRK"), ("BELARUS", "Belarus"), ("Belarus", "Belarus"), ("PAARSSR", "Syria"), ("Syria", "Syria"), ("VENEZUELA", "Venezuela"), ("Venezuela", "Venezuela")):
                if key in p and name not in g:
                    g.append(name)
    return g


def coverage(e):
    lists = {l["list"] for l in e["listings"]}
    if len(lists) == 2:
        return "both"
    return "OFAC-only" if "OFAC SDN" in lists else "UK-only"


def md(s):
    return (s or "").replace("|", "\\|")


def all_bics(e):
    out = [(b["bic"], b["source"]) for b in e["bics"]]
    listed8 = {b["bic"][:8] for b in e["bics"]}
    for lei, r in G["results"].get(e["id"], {}).items():
        for b in r["mapping_bics"]:
            if b[:8] not in listed8:
                out.append((b, f"GLEIF BIC-to-LEI mapping → {lei}"))
    return out


def leis(e):
    return G["results"].get(e["id"], {})


def summary_rows():
    rows = []
    for i, e in enumerate(ENT, 1):
        ids = []
        for l in e["listings"]:
            ids.append(("OFAC " if l["list"] == "OFAC SDN" else "UK ") + l["entry_id"])
        nl = "yes" if e["non_latin"] else "no"
        if e["entity_type"] == "bank":
            b = all_bics(e)
            bic = ", ".join(sorted({x[0][:8] + (" (GLEIF)" if x[1].startswith("GLEIF") else "") for x in b})) or "**none**"
        else:
            bic = "n/a"
        lei = ", ".join(f"`{k}`" for k in leis(e)) if e["entity_type"] != "individual" else "n/a"
        rows.append(f"| {i} | `{e['id']}` | {e['entity_type']} | {', '.join(groups(e))} | {coverage(e)} | {', '.join(ids)} | {nl} | {bic} | {lei or '—'} | {REL.get(e['id'], '—')} |")
    return rows


def detail(e):
    L = []
    title = {"bank": "Bank", "corporate": "Corporate", "individual": "Individual"}[e["entity_type"]]
    L.append(f"#### `{e['id']}` ({title})")
    L.append("")
    L.append("- **Listings**")
    for l in e["listings"]:
        if l["list"] == "OFAC SDN":
            L.append(f"  - OFAC SDN UID `{l['entry_id']}`: programmes {', '.join('`'+p+'`' for p in l['programmes'])}; SDN listing date {l['designation_date']}")
        else:
            extra = f"; OFSI Group ID {l['ofsi_group_id']}" if l["ofsi_group_id"] else "; no OFSI Group ID"
            un = f"; UN ref {l['un_ref']}" if l["un_ref"] else ""
            L.append(f"  - UK Sanctions List `{l['entry_id']}`: {l['programmes'][0]}; designated {l['designation_date']}; last updated {l['last_updated']}; source {l['designation_source']}{extra}{un}")
    prim = [n for n in e["names"] if n["name_type"] == "primary"]
    L.append("- **Primary name**: " + "; ".join(f"{md(n['value'])} ({n['listing']})" for n in prim))
    others = [n for n in e["names"] if n["name_type"] != "primary"]
    if others:
        L.append("- **Aliases** (weak and low-quality excluded): " + "; ".join(f"{md(n['value'])} *({n['name_type']}, {n['listing']})*" for n in others))
    else:
        L.append("- **Aliases**: none")
    if e["non_latin"]:
        L.append("- **Non-Latin names**: " + "; ".join(f"{md(n['value'])} *({n['name_type'] if n['name_type']!='non-latin' else 'UK non-Latin name'}; script {n['script'] or 'not stated'}; language {n['language'] or 'not stated'}; {n['listing']})*" for n in e["non_latin"]))
    else:
        L.append("- **Non-Latin names**: none on either list")
    weak = (e.get("weak_excluded_ofac") or []) + (e.get("weak_excluded_uk") or [])
    if weak:
        L.append("- **Excluded weak aliases**: " + "; ".join(md(w) for w in weak))
    if e["entity_type"] == "individual":
        ind = e["individual"]
        def fmt(k):
            vals = ind.get(k) or []
            return "; ".join(f"{v} ({s})" for v, s in vals) or "not listed"
        L.append(f"- **Date of birth**: {fmt('dob')}")
        L.append(f"- **Place of birth**: {fmt('pob')}")
        L.append(f"- **Nationalities**: {fmt('nationality')}")
        rc = ind.get("residence_countries") or []
        L.append(f"- **Country of residence**: " + (f"{', '.join(rc)}; country of listed address, neither list has a residence field ({', '.join(ind['residence_sources'])})" if rc else "not listed"))
        if e["uk_positions"]:
            L.append("- **Positions (UK)**: " + "; ".join(md(p) for p in e["uk_positions"]))
        if e["ofac_titles"]:
            L.append("- **Title (OFAC)**: " + "; ".join(md(p) for p in e["ofac_titles"]))
    else:
        if e["addresses"]:
            L.append("- **Addresses**")
            for a in e["addresses"]:
                parts = [*a["lines"], a["city"], a["region"], a["postcode"]]
                L.append(f"  - {md(', '.join(p for p in parts if p))}; country {a['country'] or 'not stated'} → `{a['iso'] or '??'}` ({a['source']})")
        else:
            L.append("- **Addresses**: none listed")
        if e["ids"]:
            L.append("- **Registration numbers and LEIs on the Listings**: " + "; ".join(f"{i['type']} `{md(i['value'])}`{' ('+i['country']+')' if i['country'] else ''} ({i['source']})" for i in e["ids"]))
        if e["uk_entity_types"]:
            L.append("- **UK type of entity**: " + ", ".join(e["uk_entity_types"]))
        if e["entity_type"] == "bank":
            b = all_bics(e)
            L.append("- **BICs**: " + ("; ".join(f"`{x}` ({s})" for x, s in b) if b else "**none found on either list or in GLEIF**"))
        lr = leis(e)
        if lr:
            L.append("- **GLEIF LEI records**")
            for lei, r in lr.items():
                L.append(f"  - `{lei}`: {md(r['legal_name'])}; {r['country']}; registeredAs {r['registered_as'] or '—'}; entity {r['entity_status']}, registration {r['registration_status']} (last update {r['last_update'][:10]}); found via {'; '.join(r['found_via'])}")
        else:
            L.append("- **GLEIF LEI**: none found")
    L.append("")
    return "\n".join(L)


def counts():
    c = Counter(e["entity_type"] for e in ENT)
    cov = Counter(coverage(e) for e in ENT)
    covt = Counter((e["entity_type"], coverage(e)) for e in ENT)
    g = Counter(x for e in ENT for x in groups(e))
    nl = sum(1 for e in ENT if e["non_latin"])
    nlt = Counter(e["entity_type"] for e in ENT if e["non_latin"])
    gt = Counter((e["entity_type"], x) for e in ENT for x in groups(e))
    return {"types": c, "coverage": cov, "coverage_by_type": covt, "groups": g, "groups_by_type": gt, "non_latin": nl, "non_latin_by_type": nlt}


if __name__ == "__main__":
    with open("gen_table.md", "w") as f:
        f.write("| # | id | Type | Programme | Lists | Listing IDs | Non-Latin | BIC | LEI | Control Relationship |\n|---|---|---|---|---|---|---|---|---|---|\n")
        f.write("\n".join(summary_rows()) + "\n")
    with open("gen_detail.md", "w") as f:
        for t in ("bank", "corporate", "individual"):
            f.write({"bank": "### Banks\n\n", "corporate": "### Corporates\n\n", "individual": "### Individuals\n\n"}[t])
            for e in ENT:
                if e["entity_type"] == t:
                    f.write(detail(e) + "\n")
    c = counts()
    for k, v in c.items():
        print(k, v)
    print(D["meta"], G["mapping_file"])
