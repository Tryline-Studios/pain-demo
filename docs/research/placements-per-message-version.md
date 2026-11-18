# Placements and fields per Message Version

Research for [#2](https://github.com/Tryline-Studios/pain-workbench/issues/2). Question: for each pain.001 Message Version that pain001 supports (.03 to .13), which party roles exist, how agents are identified, what remittance information allows, how names and addresses are structured, and whether pain001's flat pipeline (`template.csv` columns plus the Jinja `template.xml`) actually emits each role, or whether a Placement needs a custom template.

## Short answer

- **The schemas put no limits on Placement.** Every Message Version from .03 to .13 declares every role in the Placement list: Debtor, Ultimate Debtor (at payment and at transaction level), Debtor Agent, Intermediary Agents 1 to 3, Creditor Agent, Creditor, Ultimate Creditor, unstructured and structured remittance. Every party and agent name is `Max140Text`. The only differences between versions are how agents are identified (`BIC` in .03, `BICFI` from .04, a looser BIC pattern plus `LEI` from .09) and how many address fields there are (more from .09, longer again from .12).
- **pain001's flat pipeline can't cover every Placement.** `generate_xml_string` with the bundled `template.xml`:
  - never emits Intermediary Agents 1 to 3 in any version.
  - in **.04 to .08** also drops Ultimate Debtor, Ultimate Creditor, agent names and unstructured remittance. In these versions the only places a name can go are Debtor `Nm` and Creditor `Nm`.
  - in **.03 and .09 to .13** emits Debtor, Debtor Agent (BIC + name + town/country), Ultimate Debtor (name only, payment level only), Creditor Agent, Creditor, Ultimate Creditor (name only), one `Ustrd` and one `Strd` (creditor reference + one `AddtlRmtInf`).
- **You don't need a custom template.** pain001 0.0.70 also has `pain001.corpus.build(scenario, version)`, a version-aware dict-to-XML builder. It emits **every** role in **every** version .03 to .13, including `IntrmyAgt1-3`, agent name and address, full party addresses, transaction-level Ultimate Debtor, repeated `Ustrd` and `Strd/Invcr`/`Invcee`. It renames `BIC`/`BICFI` for each version and validates the output against the XSD. I checked all 11 versions with one all-roles scenario (see [Evidence](#evidence-probe-runs)). The upstream docs call it a maintainer and corpus tool, not the headline generation API. Treat it as a less stable surface.
- **Neither path allows more than one Debtor per Sample File.** Both render a single `PmtInf`, so a file has exactly one Debtor and one Debtor Agent. Only Ultimate Debtor (with the builder) and the transaction-level roles can differ per transaction.

## Sources and version pinned

- **pain001 0.0.70**, the latest on PyPI at the time of research. Wheel: `pain001-0.0.70-py3-none-any.whl` from files.pythonhosted.org (`pain001/__init__.py:19` `__version__ = "0.0.70"`). I also shallow-cloned `github.com/sebastienrousseau/pain001`. Its HEAD (9027591) is one CI-only commit past the `v0.0.70` release commit (eb89653), and `diff -rq` of the wheel's `pain001/` against the clone's `pain001/` showed no differences. All `file:line` citations below are into that wheel, relative to the `pain001/` package root.
- **XSDs:** the ISO 20022 schemas that pain001 bundles at `templates/pain.001.001.XX/pain.001.001.XX.xsd`. These are copies shipped by the library. I didn't compare them byte-for-byte with iso20022.org. Element paths and line numbers were read with lxml.
- **Empirical probes:** I ran `generate_xml_string` and `pain001.corpus.build` for all 11 versions in a scratch venv (Python 3.13, `pain001==0.0.70`, `lxml`).

## 1. What the XSDs allow (all versions)

### Where each role sits

| Role | XSD element path | Multiplicity | Present in |
|---|---|---|---|
| Debtor | `CstmrCdtTrfInitn/PmtInf/Dbtr` | 1..1 per `PmtInf` | .03 to .13 |
| Debtor Agent | `PmtInf/DbtrAgt` | 1..1 per `PmtInf` | .03 to .13 |
| Ultimate Debtor | `PmtInf/UltmtDbtr` **and** `PmtInf/CdtTrfTxInf/UltmtDbtr` | 0..1 each | .03 to .13 |
| Intermediary Agent 1/2/3 | `CdtTrfTxInf/IntrmyAgt1`, `IntrmyAgt2`, `IntrmyAgt3` | 0..1 each | .03 to .13 |
| Creditor Agent | `CdtTrfTxInf/CdtrAgt` | 0..1 | .03 to .13 |
| Creditor | `CdtTrfTxInf/Cdtr` | 0..1 | .03 to .13 |
| Ultimate Creditor | `CdtTrfTxInf/UltmtCdtr` | 0..1 | .03 to .13 |
| Remittance, unstructured | `CdtTrfTxInf/RmtInf/Ustrd` | 0..unbounded, each `Max140Text` | .03 to .13 |
| Remittance, structured | `CdtTrfTxInf/RmtInf/Strd` | 0..unbounded | .03 to .13 |
| (bonus) Invoicer / Invoicee | `RmtInf/Strd/Invcr`, `Strd/Invcee` (party type, has `Nm`) | 0..1 each | .03 to .13 |
| (bonus) Initiating Party | `GrpHdr/InitgPty` | 1..1 | .03 to .13 |

Line citations for the transaction-level roles (`IntrmyAgt1/2/3`, then `Ustrd`):

| Version | `IntrmyAgt1/2/3` | `Ustrd` |
|---|---|---|
| .03 | xsd:251/253/255 | :780 |
| .04 | :232/234/236 | :802 |
| .05 | :216/218/220 | :769 |
| .06 | :216/218/220 | :800 |
| .07 | :216/218/220 | :843 |
| .08 | :216/218/220 | :849 |
| .09 | :229/231/233 | :922 |
| .10 | :261/263/265 | :1049 |
| .11 | :261/263/265 | :1052 |
| .12 | :262/264/266 | :1042 |
| .13 | :281/283/285 | :1073 |

`PmtInf/UltmtDbtr` is at .03 xsd:652, .04 :674, .09 :762, .13 :930. `CdtTrfTxInf/UltmtDbtr` is at .03 xsd:250, .09 :228, .13 :280.

Two cross-element rules come from the ISO MDR, not the XSD. pain001 encodes both in `corpus/rules/mdr.py`:
- `UltmtDbtr` may appear at payment level or at transaction level, but not both (`corpus/rules/mdr.py:395`, `UltimateDebtorRule`).
- `IntrmyAgt2` requires `IntrmyAgt1`, and `IntrmyAgt3` requires `IntrmyAgt2` (`corpus/rules/mdr.py:320-338`).

The XSD alone accepts files that break these rules.

### Party types (Debtor, Creditor, Ultimate Debtor/Creditor, Invoicer/Invoicee)

| Version | Party type | Postal address type | Name |
|---|---|---|---|
| .03 | `PartyIdentification32` (xsd:625-629) | `PostalAddress6` | `Nm` `Max140Text` |
| .04 to .08 | `PartyIdentification43` (.04 xsd:646-650, .08 :688-692) | `PostalAddress6` | `Nm` `Max140Text` |
| .09 to .11 | `PartyIdentification135` (.09 xsd:733-737) | `PostalAddress24` | `Nm` `Max140Text` |
| .12 to .13 | `PartyIdentification272` (.12 xsd:868-872, .13 :893-897) | `PostalAddress27` | `Nm` `Max140Text` |

In every version the party type's children are `Nm`, `PstlAdr`, `Id`, `CtryOfRes`, and `CtctDtls`.

Name structure is identical in every version: a single free-text `Nm`, `Max140Text` (minLength 1, maxLength 140). There are no separate given-name or family-name fields.

Address structure:

| Type | Versions | Fields |
|---|---|---|
| `PostalAddress6` | .03 to .08 (.03 xsd:701-710) | `AdrTp` (code), `Dept`, `SubDept`, `StrtNm` (70), `BldgNb` (16), `PstCd` (16), `TwnNm` (35), `CtrySubDvsn` (35), `Ctry`, `AdrLine` 0..7 x `Max70Text` |
| `PostalAddress24` | .09 to .11 (.09 xsd:809-824) | Adds `BldgNm`, `Flr`, `PstBx`, `Room`, `TwnLctnNm`, `DstrctNm`. `AdrTp` becomes a `Cd`/`Prtry` choice. `AdrLine` is still 0..7 x 70. |
| `PostalAddress27` | .12 to .13 (.12 xsd:952-969) | Adds `CareOf` (140) and `UnitNb`. `StrtNm`, `BldgNm`, `TwnNm`, `TwnLctnNm` and `DstrctNm` widen to `Max140Text`. |

All address elements are optional, and structured fields and `AdrLine` can be mixed.

### Agent identification

| Version | Agent type / `FinInstnId` type | BIC element and pattern | Other children |
|---|---|---|---|
| .03 | `BranchAndFinancialInstitutionIdentification4` / `FinancialInstitutionIdentification7` (xsd:443-447) | **`BIC`** (`BICIdentifier`, `[A-Z]{6}[A-Z2-9][A-NP-Z0-9]([A-Z0-9]{3})?`) | `ClrSysMmbId`, `Nm` (140), `PstlAdr` (`PostalAddress6`), `Othr` |
| .04 to .08 | `...Identification5` / `FinancialInstitutionIdentification8` (.04 xsd:458-462, .08 :482-486) | **`BICFI`** (`BICFIIdentifier`, same pattern) | same as .03 |
| .09 to .11 | `...Identification6` / `FinancialInstitutionIdentification18` (.09 xsd:506-511) | **`BICFI`** (`BICFIDec2014Identifier`, `[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?`) | adds **`LEI`**; `PstlAdr` is `PostalAddress24` |
| .12 to .13 | `...Identification8` / `FinancialInstitutionIdentification23` (.12 xsd:568-573, .13 :593-598) | `BICFI` (Dec2014 pattern) | `LEI`, `Nm` (140), `PstlAdr` (`PostalAddress27`) |

All children of `FinInstnId` are optional, so an agent can be identified by name and address alone, with no BIC. `BrnchId` (with its own `Nm` and `PstlAdr`) is also available on every agent.

### Remittance information

- `RmtInf` is 0..1 per transaction and holds `Ustrd` (0..unbounded x `Max140Text`) and `Strd` (0..unbounded) in every version (.03 xsd:780-781 ... .13 :1073-1074).
- `Strd` children:
  - .03 to .05: `RfrdDocInf`, `RfrdDocAmt`, `CdtrRefInf` (`Ref` `Max35Text`), `Invcr`, `Invcee`, `AddtlRmtInf` 0..3 x `Max140Text` (.03 xsd:822-827).
  - .06 adds `TaxRmt` and `GrnshmtRmt` (.06 xsd:850-851). Garnishment carries further party names: `Grnshee` and `GrnshmtAdmstr`.
  - .13 adds `SctiesData` (.13 xsd:1131).
- Places in remittance where free text or a name can go:
  - `Ustrd` (140 each, repeatable)
  - `Strd/AddtlRmtInf` (140, up to 3)
  - `Strd/Invcr/Nm` and `Strd/Invcee/Nm` (140)
  - `CdtrRefInf/Ref` (35 only)

## 2. What pain001's flat pipeline emits

### How the pipeline works

`generate_xml_string` (`xml/generate_xml.py:309`) normalises the rows, calls `prepare_xml_data(rows, message_type)` (`xml/message_registry.py:641-645`) to build a Jinja context, renders `template.xml`, and validates the result against the XSD (`generate_xml.py:375-434`). The registry maps each version to a preparer:

| Versions | Preparer | Where |
|---|---|---|
| .03 | `_prepare_xml_data_v03` | `message_registry.py:110-153`; reuses the modern context via `_context_v09` |
| .04 | `_prepare_xml_data_v04` | `:156-235` |
| .05 to .08 | `_prepare_xml_data_v05_to_v08` | `:238-313` |
| .09 to .13 | `_prepare_xml_data_v09_to_v12` | `:399-517` |

The registry itself is at `message_registry.py:577-630`.

Template files:
- The .10, .11 and .12 `template.xml` files are byte-identical to .09 apart from the namespace.
- .13 differs only in `RgltryRptg` (`DbtCdtRptgInd` defaults to `CRED`, and `Dtls/Cd` becomes `RptgCd`).
- The .06 and .07 templates are identical to .05 apart from the namespace.
- .08 differs from .05 only in `ReqdExctnDt/Dt`.

`template.csv` in each version directory is **example data only** (`templates/pain.001.001.03/metadata.yaml`: `example_data: template.csv`). The columns a template really consumes are the keys its preparer reads. The two don't match:
- .05 `template.csv` has `ultimate_debtor_name`, and the .05-.08 preparer maps it (`message_registry.py:257`), but the .05 template never renders it.
- Every version's CSV has a `forwarding_agent_BIC` column that no preparer reads.

### Version x role matrix

Legend:
- **XSD**: declared by the schema.
- **Flat**: emitted by `generate_xml_string` with the bundled `template.xml`.
- **Builder**: emitted by `pain001.corpus.build`.
- ✓ = yes, ✗ = no.

| Role | XSD .03-.13 | Flat .03 | Flat .04-.08 | Flat .09-.13 | Builder .03-.13 |
|---|---|---|---|---|---|
| Debtor `Nm` | ✓ | ✓ header row only | ✓ header row only | ✓ header row only | ✓ one per file |
| Debtor `PstlAdr` | ✓ | ✓ structured + 1 `AdrLine` | ✓ StrtNm/BldgNb/PstCd/TwnNm/Ctry, **all required** | ✓ structured + 1 `AdrLine` | ✓ structured / hybrid / unstructured |
| Debtor Agent BIC | ✓ | ✓ `BIC` | ✓ `BICFI` | ✓ `BICFI` | ✓ renamed per version |
| Debtor Agent `Nm` / `PstlAdr` | ✓ | ✓ name + TwnNm/CtrySubDvsn/Ctry | ✗ BICFI only | ✓ name + TwnNm/CtrySubDvsn/Ctry | ✓ name + full address, `LEI`, `BrnchId` |
| Ultimate Debtor, payment level | ✓ | ✓ `Nm` only | ✗ | ✓ `Nm` only | ✓ full party |
| Ultimate Debtor, transaction level | ✓ | ✗ | ✗ | ✗ | ✓ full party |
| Intermediary Agent 1-3 | ✓ | ✗ | ✗ | ✗ | ✓ BIC + name + address |
| Creditor Agent BIC | ✓ | ✓ | ✓ | ✓ | ✓ |
| Creditor Agent `Nm` / `PstlAdr` | ✓ | ✓ name + town/country | ✗ | ✓ name + town/country | ✓ |
| Creditor `Nm` | ✓ | ✓ per transaction | ✓ per transaction | ✓ per transaction | ✓ |
| Creditor `PstlAdr` | ✓ | ✓ structured + 1 `AdrLine` | ✓ **4 `AdrLine`, all required** | ✓ structured + 1 `AdrLine` | ✓ |
| Creditor `Id` | ✓ | ✗ | ✗ | ✗ | ✓ |
| Ultimate Creditor | ✓ | ✓ `Nm` only | ✗ | ✓ `Nm` only | ✓ full party |
| `RmtInf/Ustrd` | ✓ unbounded | ✓ one | ✗ | ✓ one | ✓ list |
| `RmtInf/Strd` | ✓ unbounded | ✓ one: `RfrdDocInf`, `CdtrRefInf`, one `AddtlRmtInf` | ✓ one: `RfrdDocInf` only (**required**) | ✓ one: `CdtrRefInf` (required to trigger) + one `AddtlRmtInf` | ✓ list: docs, amounts, `CdtrRefInf`, `Invcr`, `Invcee`, `AddtlRmtInf` |
| `Strd/Invcr`, `Strd/Invcee` | ✓ | ✗ | ✗ | ✗ | ✓ |

Citations for the Flat columns.

**.03 and .09-.13** (`templates/pain.001.001.03/template.xml` and `templates/pain.001.001.09/template.xml`):

| What | .03 lines | .09 lines |
|---|---|---|
| address macro (single `AdrLine`) | 5-31 | 4-30 |
| agent macro (BIC/BICFI, `ClrSysMmbId`, `Nm`, `PstlAdr` with only `TwnNm`/`CtrySubDvsn`/`Ctry`) | 52-84 | 56-88 |
| `Dbtr` | 155-159 | 165-169 |
| `DbtrAgt` | 163-165 | 173-175 |
| `UltmtDbtr` (name only, `PmtInf` level) | 166-170 | 176-180 |
| `CdtrAgt` | 181-183 | 196-198 |
| `Cdtr` (name + address, no `Id`) | 184-187 | 199-202 |
| `UltmtCdtr` (name only) | 191-195 | 206-210 |
| `RmtInf` | 219-258 | 234-263 |

The preparer builds these values as follows:
- Agent: BIC, member id, name, and town/subdivision/country only (`message_registry.py:347-360`).
- Address: street, building, postcode, town, subdivision, country, one `address_line` (`message_registry.py:322-334`).
- Ultimate debtor: taken from the header row only (`message_registry.py:514`).
- Ultimate creditor: name only (`message_registry.py:469`).
- One `remittance_information` string per transaction (`message_registry.py:472-474`).
- Debtor, debtor account and debtor agent: taken from `data[0]` (`message_registry.py:436`, `:507-513`).

**.04-.08** (`templates/pain.001.001.04/template.xml` and `.05/template.xml`):
- `DbtrAgt` and `CdtrAgt` are a bare `BICFI` (.04 lines 42-46 and 58-62).
- `Cdtr/PstlAdr` is four unconditional `AdrLine` elements (.04 lines 63-71).
- `Purp` and `RmtInf/Strd/RfrdDocInf` are unconditional (.04 lines 79-89).
- The template has no `UltmtDbtr`, `UltmtCdtr`, `Ustrd` or agent `Nm`.
- The .05-.08 preparer passes `remittance_information` (`message_registry.py:307`), but no template renders it.
- These templates have no `{% if %}` guards, so every field is required in practice. A row with no debtor address, creditor address, `charge_bearer`, `purpose_code` or `reference_number` fails XSD validation (see the probe below).

**No version:** `grep -rni "intrmy|intermediary"` over the package finds hits only in `corpus/` (`corpus/builder.py:525-592`, `corpus/rules/mdr.py`, `corpus/coverage_sets.py`). Nothing in `xml/`, `templates/*/template.xml` or `schemas/` matches.

### The corpus builder (`pain001.corpus.build`)

- **Entry point.** `build(scenario: Scenario | dict, version: str, patch=None) -> BuildResult` (`corpus/builder.py:886-929`), exported from `pain001.corpus` (`corpus/__init__.py:35-41`). The scenario is a dict validated by `corpus/schema/corpus.schema.json`: required `id`, `family`, `country`, `versions`, `payment`, `transactions` (`corpus/registry.py:123-151`).
- **Roles.** `_Composer.compose` / `transaction` map friendly keys to every role:
  - `payment.debtor`, `debtor_agent`, `ultimate_debtor` (`builder.py:690-699`)
  - `transactions[].ultimate_debtor`, `intermediary_agents[0..2]`, `creditor_agent`, `creditor`, `ultimate_creditor`, `remittance` (`builder.py:525-601`)
  - parties: name, address, id, country of residence, contact (`builder.py:156-178`)
  - agents: BICFI, clearing, LEI, name, address, branch (`builder.py:342-387`)
  - addresses: structured, hybrid or unstructured forms (`builder.py:257-306`)
  - remittance: `Ustrd` list plus `Strd` list with `Invcr`/`Invcee` (`builder.py:415-487`)
  - `raw` merges let a scenario inject any ISO element the friendly layer doesn't name (`builder.py:120-129`).
- **Version fitting.** The `_Fitter` walks the version's XSD inventory:
  - renames `BIC`/`BICFI` and `BICOrBEI`/`AnyBIC` (`builder.py:55-60`, `:741-746`)
  - wraps and unwraps choices, truncates repeats to the version's cap, drops undeclared elements and records it in `BuildReport`
  - sorts children into schema order (`builder.py:718-805`)
  - then validates against the bundled XSD and raises `BuildError` on failure (`builder.py:917-928`).
- **Determinism.** Output is deterministic: `auto` identifiers are derived from `scenario.seed` (`builder.py:147-152`, `registry.py:81-89`), and the builder docstring says a rebuild is byte-identical (`builder.py:39-40`). This fits the Seed concept.
- **Caveats:**
  - Serialisation imports `lxml` lazily (`builder.py:810-811`). lxml is only in the `fast` extra (wheel METADATA `Requires-Dist: lxml ... ; extra == "fast"`), so depend on `pain001[fast]`.
  - The comment at `builder.py:810` calls the builder "a maintainer tool". Upstream ADR-0003 (repo `docs/adr/0003-example-corpus-two-corpora-one-engine.md`, decision 6) frames it as the engine that builds pain001's example corpus, with the CSV pipeline to be "extended afterwards … with the corpus as the golden target". `docs/corpus.md` shows `from pain001.corpus.builder import build` as a supported use for private bank variants. The package docstring says it "grows over the 0.0.67 to 0.0.69 releases" (`corpus/__init__.py:17`). So it is new (0.0.67, September 2026) and more likely to change than `generate_xml_string`.
  - It doesn't run the MDR rules; `build` only checks the XSD. `corpus.rules.mdr.evaluate_mdr(xml)` (`corpus/rules/mdr.py:550`) is available separately.
  - `payment` is a single object, so there is one `PmtInf` and one Debtor per file (`builder.py:621`, `:650-710`).

## Evidence: probe runs

pain001 0.0.70, Python 3.13, 2026-09-16. Rows and the scenario put a marker string `SANCTIONED NAME` into every name and free-text field that each path accepts.

`generate_xml_string` with a full two-transaction row set:

```
.03        OK  emits InitgPty Dbtr DbtrAgt UltmtDbtr CdtrAgt Cdtr UltmtCdtr Ustrd Strd | missing IntrmyAgt1-3 Invcr Invcee | BIC
.04-.08    OK  emits InitgPty Dbtr DbtrAgt CdtrAgt Cdtr Strd | missing UltmtDbtr IntrmyAgt1-3 UltmtCdtr Ustrd Invcr Invcee | BICFI
           marker lands only in Dbtr/Nm and Cdtr/Nm
.09-.13    OK  same as .03 but BICFI
           marker lands in Dbtr/Nm, DbtrAgt/FinInstnId/Nm, UltmtDbtr/Nm, CdtrAgt/FinInstnId/Nm, Cdtr/Nm, UltmtCdtr/Nm, Ustrd, Strd/AddtlRmtInf
Two rows with different debtor_name: second debtor absent, one <PmtInf>.
```

`generate_xml_string` with a minimal row (no addresses, `purpose_code`, `charge_bearer` or reference):

```
.03, .09-.13  OK
.04-.08       FAIL (XSD): ChrgBr enumeration, Cdtr/PstlAdr/AdrLine[1-4] empty, Purp/Cd empty,
              RmtInf/Strd/RfrdDocInf/Nb empty, RltdDt invalid date
```

`pain001.corpus.build` with one all-roles scenario: payment-level and transaction-level `UltmtDbtr`, three intermediary agents with BIC + name + address, `Invcr`/`Invcee`:

```
.03-.13  OK, XSD-valid, no role missing, nothing dropped; .03 report: renamed BICFI -> BIC
         marker lands in every Nm (all parties, all agents incl. IntrmyAgt1-3, Invcr, Invcee), Ustrd, AddtlRmtInf
```

## Implications for Placement support

1. **The Placement list is the same for every Message Version.** A Placement doesn't need a per-version availability table based on the schema. The differences are in rendering: the `BIC`/`BICFI` tag, the BIC pattern (Dec2014 from .09), `LEI` on agents from .09, and address field set and lengths (70 vs 140 for street and town from .12). Names are `Max140Text` everywhere, which bounds Name Variants such as fuzzed or transliterated forms.
2. **With the flat pipeline, Placement availability depends on the version:**
   - Intermediary Agent is impossible in every version.
   - In .04-.08, only Debtor and Creditor would be supported, and every optional field would have to be populated to pass the XSD.
   - In .03 and .09-.13, Ultimate Debtor and Ultimate Creditor would be name-only, and Ultimate Debtor would be payment-level only.

   Supporting the full Placement list on this path needs custom `template.xml` files. A custom template alone wouldn't be enough either, because the preparers don't pass intermediary-agent or ultimate-party-address keys. We would need our own preparer, or to bypass `prepare_xml_data`.
3. **`pain001.corpus.build` covers every Placement in every version without custom templates.** It also handles version spelling and XSD validation. Adopting it means depending on a newer, maintainer-oriented surface. That's a decision for the generation-engine ticket, not a fact settled here.
4. **Debtor and Debtor Agent Placements are one per Sample File on both paths** (single `PmtInf`). Placing different Sanctioned Entities as Debtor in the same file would need several `PmtInf` blocks, which neither path produces without extra work. Ultimate Debtor at transaction level, via the builder, can vary per transaction.
5. **"Remittance information" as a Placement has more than one target.** The candidates are `Ustrd` (140, repeatable), `Strd/AddtlRmtInf` (140, up to 3), and the names in `Strd/Invcr` and `Strd/Invcee`. `CdtrRefInf/Ref` (35) is too short for most entity names. The Answer Key should record which element was used.
6. **Placement candidates outside the ticket's list** that the XSD also offers: Initiating Party, `BrnchId` names on agents, and Garnishment parties (`Grnshee`, `GrnshmtAdmstr`, from .06).
