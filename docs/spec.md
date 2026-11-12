# pain.001 Sample File generator: build-ready spec

This is the build-ready specification for the pain.001 Sample File generator. It is assembled from the resolved tickets of the wayfinder map ([Wayfinder: pain.001 Sample File generator spec](https://github.com/Tryline-Studios/pain-demo/issues/1)). Every section names the ticket it comes from. Where this document and a ticket disagree, the ticket's resolution comment is the source of truth, and the disagreement belongs in [Open points found while assembling](#open-points-found-while-assembling).

Domain terms (Sample File, Message Version, Entity Catalogue, Clean Bank List, Placement, Hit, Exposure, Name Variant, Native Script, Transliteration, Answer Key, Seed, Generator Version, Effective Request, Screening Tool and the rest) are defined once, in [`CONTEXT.md`](../CONTEXT.md). This document uses them without redefining them.

Contents:

1. [Purpose and scope](#1-purpose-and-scope)
2. [Architecture and repo layout](#2-architecture-and-repo-layout)
3. [Entity Catalogue](#3-entity-catalogue)
4. [Clean Bank List and unplanned-hit screening](#4-clean-bank-list-and-unplanned-hit-screening)
5. [Generation: request model and Supplied Data merging](#5-generation-request-model-and-supplied-data-merging)
6. [Placement selection and overrides](#6-placement-selection-and-overrides)
7. [Name Variants](#7-name-variants)
8. [Exposures](#8-exposures)
9. [Seed, randomness and Generator Version](#9-seed-randomness-and-generator-version)
10. [Rendering engine and version fitting](#10-rendering-engine-and-version-fitting)
11. [Answer Key](#11-answer-key)
12. [API contract](#12-api-contract)
13. [Web UI](#13-web-ui)
14. [Observability](#14-observability)
15. [Testing, CI and upgrade procedures](#15-testing-ci-and-upgrade-procedures)
16. [Configuration](#16-configuration)
17. [Upload Validation](#17-upload-validation)

Appendix A: [ADR index](#appendix-a-adr-index). Appendix B: [Ticket index](#appendix-b-ticket-index). Then [Open points found while assembling](#open-points-found-while-assembling).

---

## 1. Purpose and scope

Source: the map's Destination and Notes ([Wayfinder: pain.001 Sample File generator spec](https://github.com/Tryline-Studios/pain-demo/issues/1)), plus the Out of scope lines from [Entity Catalogue contents and schema](https://github.com/Tryline-Studios/pain-demo/issues/6), [Placement selection and overrides](https://github.com/Tryline-Studios/pain-demo/issues/9), [Observability](https://github.com/Tryline-Studios/pain-demo/issues/17), [Multi-version batch generation](https://github.com/Tryline-Studios/pain-demo/issues/18) and [SWIFT character set restriction](https://github.com/Tryline-Studios/pain-demo/issues/20).

### 1.1 Purpose

The app generates ISO 20022 pain.001 (Customer Credit Transfer Initiation) Sample Files for testing and proving a sanctions payment Screening Tool. A Sample File mixes Generated Data with real Sanctioned Entities from the Entity Catalogue, or with Supplied Data from the user, and ships with an Answer Key that states exactly what the Screening Tool should flag.

### 1.2 Settled constraints

- Backend: Python 3.13, FastAPI, uv, ruff, ty. Frontend: Vite, React, TypeScript, pnpm, TanStack Query, shadcn/ui, Biome, with a TypeScript client generated from the committed OpenAPI document. Deployed with docker-compose, Caddy serving the frontend and proxying `/api`.
- Our own `/api/v1` is the only public contract (ADR-0001). The UI uses only the public API; scripts and CI call it directly.
- Stateless: no database, no auth, no job queue. Internal and local use only. Synchronous generation. At most 100 transactions per Sample File.
- Every Message Version pain001 supports, pain.001.001.03 to pain.001.001.13, selectable in the UI and API. Default pain.001.001.03.
- Generated Data and/or Supplied Data (a nested JSON model or a flat CSV of the same fields). Gaps in partial Supplied Data are filled with Generated Data. Countries and currencies are set per request.
- A curated Entity Catalogue in the repo. Hit Count (0 allowed) plus optional named Hits. All Placements and all Name Variants. An Answer Key with every Sample File. An optional Seed, always echoed back.

### 1.3 Out of scope for v1

- Multi-version batch generation: scripts loop over the API instead.
- Restricting Sample File text to the SWIFT character set: the Screening Tool, not a bank gateway, is under test.
- Metrics endpoints, tracing and error-reporting services: internal single-container use; logs and a healthcheck suffice.
- Initiating Party, agent `BrnchId` and garnishment parties as Placements: rare in credit transfers, and Initiating Party is normally the Debtor.
- Loading the full OFAC or UK sanctions lists: v1 uses the curated Entity Catalogue.
- False-positive decoys (look-alike innocent names).
- Authentication and internet exposure.
- Persistence and Postgres (history, saved presets).
- Sample Files over 100 transactions, and async jobs.
- EU, UN and OFAC non-SDN sanctions lists, vessels, unlisted related parties, and derived sanctions under OFAC's 50% rule. The catalogue covers listed Entities on the OFAC SDN List and the UK Sanctions List only.
- Screening generated names against the full sanctions lists (only the Entity Catalogue is screened; see section 4).
- A deliberately-broken-file mode: Sample Files are always XSD-valid.

---

## 2. Architecture and repo layout

Source: [Repo layout, docker-compose and tooling](https://github.com/Tryline-Studios/pain-demo/issues/5), [Generation path: flat templates vs corpus.build](https://github.com/Tryline-Studios/pain-demo/issues/13), ADR-0001, ADR-0002.

### 2.1 Layout

```
.
├── backend/                       uv src-layout project, package pain_demo
│   ├── pyproject.toml             requires-python = ">=3.13,<3.14"
│   ├── .python-version            3.13
│   ├── uv.lock                    committed
│   ├── openapi.json               committed, drift-checked (section 12.5)
│   ├── src/pain_demo/
│   │   ├── catalogue/
│   │   │   ├── entities/<id>.toml           one file per Entity (section 3)
│   │   │   └── control_relationships.toml
│   │   └── generation/
│   │       └── clean_banks.toml             the Clean Bank List (section 4)
│   └── tests/                     pytest; goldens under here (section 15)
├── frontend/                      Vite + React + TypeScript, pnpm
├── compose.yaml
├── justfile
├── .editorconfig                  120 columns everywhere
├── .pre-commit-config.yaml        prek hooks
├── NOTICE                         OGL v3.0 attribution and OFAC citation
├── CONTEXT.md                     the glossary
└── docs/
    ├── spec.md                    this document
    └── adr/
```

The exact module layout inside `pain_demo` is left to implementation, with one constraint: **one renderer module holds every pain001 import** (section 10.2).

### 2.2 Runtime shape

- **Development runs natively.** `uv run fastapi dev` for the backend and `pnpm dev` for the frontend, with Vite proxying `/api` to the backend. docker-compose is for the deployable stack only.
- **Compose services:**
  - `api`: uvicorn running the FastAPI app.
  - `web`: Caddy serving the built React app and forwarding `/api/*` to `api`.
- Only `localhost:8080` is published, plain HTTP, Caddy's automatic HTTPS off.
- Two-stage image builds: `ghcr.io/astral-sh/uv` to `python:3.13-slim` for `api`; `node` to `caddy` for `web`.
- Healthchecks on both services; `web` waits for `api` to be healthy. `api`'s healthcheck hits `GET /api/v1/health` (section 12.1).
- Deployment builds on the host: `git pull && just up`. No registry, no multi-arch images.
- No CORS middleware: Caddy serves UI and API on one origin, and the native dev loop uses Vite's proxy.

### 2.3 Tooling

- **Tasks:** `just` recipes. Known recipes: `check`, `test`, `up`, `gen-client`, `openapi`, `verify-catalogue`, `verify-clean-banks`, `build-clean-banks`, `upgrade-generators`. See section 15 for what each does.
- **Python quality:** `ruff format` and ruff lint at line length 120, rules `E, F, I, UP, B, SIM, RUF, ASYNC, FAST, PT, S` (`S` off in tests). `ty check`, pinned exactly, default rules; any diagnostic fails CI.
- **Frontend:** pure TypeScript. No `.js`, `.jsx` or `.mjs`; config files are `.ts`. tsconfig: `allowJs: false`, `strict`, `noUncheckedIndexedAccess`, `noImplicitOverride`, `verbatimModuleSyntax`; no `exactOptionalPropertyTypes`. Biome at `lineWidth: 120`, banning `any` and non-null assertions. Node 24 LTS pinned in `.nvmrc` and `.node-version`; pnpm pinned via `packageManager` and corepack. Docker builds use the same pins.
- **API client:** a script imports the FastAPI app and writes `backend/openapi.json` with no server running. `openapi-typescript`, `openapi-fetch` and `openapi-react-query` generate the client from it. CI fails if regenerating changes anything.
- **Configuration:** `pydantic-settings` with the `PAIN_DEMO_` prefix and a committed `.env.example`. No secrets. See section 16.

### 2.4 Dependency policy

| Dependency | Pin | Dependabot | Why |
|---|---|---|---|
| `pain001[fast]` | exact (`==`) | excluded | pre-1.0, several releases a day; output must not drift (ADR-0002) |
| `Faker` | exact | excluded | seeded output changes across releases |
| `schwifty` | exact | excluded | registry and seeded output change across releases |
| `iuliia` | exact | excluded | transliteration output feeds the Seed contract |
| `rapidfuzz` | exact | excluded | similarity thresholds decide redraws, so they feed the Seed contract |
| `ty` | exact | grouped tooling | any diagnostic fails CI |
| `structlog`, FastAPI, uvicorn, pydantic, lxml (via the `fast` extra), everything else | ordinary | grouped tooling and frameworks | |

The five excluded packages are upgraded only through `just upgrade-generators` (section 15.4).

---

## 3. Entity Catalogue

Source: [Entity Catalogue contents and schema](https://github.com/Tryline-Studios/pain-demo/issues/6) with its amendments, [Entity Catalogue candidate roster](https://github.com/Tryline-Studios/pain-demo/issues/16), [Sanctions list entry shape for banks and corporates](https://github.com/Tryline-Studios/pain-demo/issues/3).

### 3.1 Scope and sources

- One catalogue Entity per real-world party, carrying one or more Listings. Every Entity, Individuals included, has at least one Listing of its own.
- A Listing is an entry on the **OFAC SDN List** (keyed by UID) or the **UK Sanctions List** (keyed by Unique ID). The OFSI Consolidated List closed on 2026-01-28; OFSI Group IDs are legacy and not issued for later designations.
- Entity Types: `individual`, or a Legal Entity that is `bank` or `corporate`. Corporate means any non-Bank Legal Entity, trusts included.
- Preferred source formats: OFAC `SDN_ADVANCED.XML` (the only OFAC file with non-Latin names and per-alias strength) and the UK Sanctions List XML (the CSV repeats entries across rows). The UK list has no BIC field; bank BICs come from OFAC or GLEIF.
- Licensing: the repo's `NOTICE` carries the OGL v3.0 attribution line ("Contains public sector information licensed under the Open Government Licence v3.0.") and the OFAC source citation.

### 3.2 Approved roster (v1)

50 Entities, verified against OFAC files dated 2026-09-14, the UK Sanctions List dated 11/09/2026, the GLEIF BIC-to-LEI mapping dated 2026-08-28 and the GLEIF API on 2026-09-16. Full write-up: [entity-catalogue-roster.md](https://github.com/Tryline-Studios/pain-demo/blob/research/entity-catalogue-roster/docs/research/entity-catalogue-roster.md) on branch `research/entity-catalogue-roster`, with parsing scripts in `docs/research/scripts/entity-catalogue-roster/`.

| Facet | Count |
|---|---|
| Banks / Corporates / Individuals | 20 / 16 / 14 |
| On both lists / OFAC-only / UK-only | 32 / 9 / 9 |
| Programmes: Russia / Iran / DPRK / Belarus / Syria / Venezuela | 27 / 7 / 5 / 4 / 4 / 4 (Evrofinance Mosnarbank counts under Russia and Venezuela) |
| With a non-Latin name (Cyrillic, Arabic/Persian, Han) | 31 |
| Banks with a BIC | 20 (17 from an OFAC Listing, 3 from GLEIF only: Russian Agricultural Bank, Alfa Bank Belarus, Bank Melli Iran) |

Roster ids:

- **Banks:** `sberbank`, `vtb-bank`, `gazprombank`, `alfa-bank`, `bank-rossiya`, `promsvyazbank`, `veb-rf`, `russian-agricultural-bank`, `t-bank`, `sberbank-europe`, `evrofinance-mosnarbank`, `bank-dabrabyt`, `belinvestbank`, `alfa-bank-belarus`, `bank-melli-iran`, `bank-mellat`, `bank-sepah`, `foreign-trade-bank-dprk`, `daedong-credit-bank`, `bandes`.
- **Corporates:** `evraz-plc`, `evraz-ntmk`, `rosneft`, `rostec`, `gazprom-neft`, `sovcomflot`, `alrosa`, `belaruskali`, `national-iranian-oil-company`, `irisl`, `mahan-air`, `komid`, `dandong-hongxiang`, `pdvsa`, `cham-holding`, `syriatel`.
- **Individuals:** `roman-abramovich`, `alexander-abramov`, `andrey-kostin`, `herman-gref`, `andrey-akimov`, `mikhail-fridman`, `yuri-kovalchuk`, `igor-sechin`, `sergey-chemezov`, `rami-makhlouf`, `fares-chehabi`, `ahmad-derakhshandeh`, `simon-zerpa`, `kim-chol-sam`.

Must-includes and accepted facts of the lists:

- Sberbank is on both lists (OFAC UID 17018 with BIC `SABRRUMM`; UK RUS0256). Evraz PLC is UK-only (RUS1027); OFAC lists Russian subsidiaries instead (e.g. UID 50054, Evraz NTMK). Roman Abramovich is UK-only (RUS0270) and appears in no OFAC file.
- No Syrian Bank is listed on either list. UK-listed Venezuelan parties are Individuals only. No Belarus Individual has a documented link to a catalogue Legal Entity.
- 12 of the 14 Individuals have a sourced Control Relationship. Two parent-company links exist: Sberbank to Sberbank Europe AG, and Evraz PLC to Evraz NTMK.

### 3.3 Schema

One TOML file per Entity at `backend/src/pain_demo/catalogue/entities/<id>.toml`, validated with Pydantic at startup.

| Field | Rule |
|---|---|
| `id` | readable, immutable slug matching the filename (e.g. `sberbank`). Used in API payloads and the Answer Key. |
| `entity_type` | `individual`, `bank` or `corporate` |
| `listings[]` | list (`ofac_sdn` or `uk`), entry ID (OFAC UID or UK Unique ID), programme or regime, designation date, and the snapshot date and source file it was verified against |
| `names[]` | value; source name type (`primary`, `primary_variation`, `aka`, `fka`, `nka`); script; `script_source` (`stated` or `derived` from the Unicode characters); language, only when the list states it; the originating Listing. **Weak and low-quality aliases are excluded entirely.** |
| Legal Entities: `addresses[]` | structured, with ISO 3166-1 alpha-2 country codes, each tied to its source Listing |
| Legal Entities: `lei`, `registration_numbers[]` | optional, each with a cited source. An LEI is stored only when its GLEIF record clearly matches the listed Entity (omitted for Bank Sepah and Evraz NTMK; kept for Sberbank Europe AG with its renamed GLEIF legal name, MeSoFa Vermögensverwaltungs AG in Abwicklung, recorded) |
| Banks: `bics[]` | each with a source (a Listing, or an external non-sanctions citation such as GLEIF's BIC-to-LEI mapping) and a verified date. Non-SWIFT codes (e.g. a Russian domestic BIK such as Evrofinance's UK "BIC 044525204") are never stored as BICs. A Bank with no BIC is allowed; it can only be placed by name and address. |
| Individuals | names, date of birth, place of birth, nationalities, `country_of_residence` only when a list states it. No ID document numbers, no personal addresses. |

Control Relationships live in `backend/src/pain_demo/catalogue/control_relationships.toml`. Each records:

- the controller Entity and the controlled Legal Entity;
- the role: `ultimate_beneficial_owner`, `controlling_shareholder`, `director`, `officer` (president, treasurer, representative and similar), or `parent_company`;
- the status: `current`, `former`, or `as_listed` (the list states the role without saying whether it still holds; dated to the Listing), with an as-of date;
- a source citation.

Startup validation (failure logs at CRITICAL and exits non-zero, section 14):

- ids are unique and match filenames;
- every Entity has at least one Listing;
- relationship references resolve, and the controlled Entity is a Legal Entity;
- BICs and LEIs are well-formed.

### 3.4 Freshness

The catalogue is a frozen snapshot. `just verify-catalogue` downloads the current OFAC SDN and UK Sanctions List files and reports drift: delisted, renamed, or BIC changed. It runs manually, never in CI, and never imports anything. A catalogue edit regenerates the goldens and bumps the minor version (section 15.4).

---

## 4. Clean Bank List and unplanned-hit screening

Source: [Keeping Generated Data free of unplanned hits](https://github.com/Tryline-Studios/pain-demo/issues/14), [Seeded fake payment data libraries](https://github.com/Tryline-Studios/pain-demo/issues/4).

### 4.1 Why

schwifty's bank registry names real sanctioned banks (Bank Melli Iran, Bank Saderat Iran, Bank Sepah, Bank Mellat, VTB Bank Georgia, Sberbank subsidiaries), so an unfiltered draw can put a Sanctioned Entity into a clean Sample File; a clean 100-transaction all-DE file had about an 8% chance. The registry also changes between releases, which would shift seeded draws.

### 4.2 The Clean Bank List

- A committed TOML file at `backend/src/pain_demo/generation/clean_banks.toml` of real, non-sanctioned banks per supported country: country, bank code, BIC, name. US entries also carry an ABA routing number.
- It is the **only** source of generated agents and accounts. schwifty is used for IBAN assembly and checksums, never for picking a bank.
- It lives beside the generation code, not inside the Entity Catalogue.
- Building it: `just build-clean-banks` takes every registry bank with a BIC for the eleven IBAN countries (GB, IE, DE, FR, IT, ES, NL, BE, PL, AT, PT), drops anything matching the Entity Catalogue by BIC or normalised name, keeps about 25 per country sorted by name for a stable output, and a human reviews the diff before committing. Household names are not required. The US entries (about 15 banks with BIC and ABA routing number) are hand-maintained in the same file; there is no US registry.

### 4.3 Keeping it clean, three layers

1. **Startup:** the app asserts the Clean Bank List shares no BIC and no normalised name with the Entity Catalogue, and refuses to start otherwise.
2. **CI:** the same assertion runs as a test over the committed files.
3. **Manual:** `just verify-clean-banks` (sibling of `just verify-catalogue`) checks every entry by name and BIC against the current OFAC SDN and UK Sanctions List files and reports matches. Never in CI, never imports anything.

Removing a bank from the list changes goldens and bumps the minor version like any generator change.

### 4.4 Generated party-name screening

Every generated party name (Faker person or company, for parties and Ultimate parties, and the romanised names of section 8) is compared with every name in the Entity Catalogue, exact and by Jaro-Winkler similarity at the fuzz threshold of 0.85 (`rapidfuzz`), and redrawn from the same per-transaction stream on a match, so determinism holds. Generated addresses and remittance sentence templates are not screened; the only names they contain are the screened ones.

### 4.5 Library usage rules

- **Faker** for names and structured address parts, one instance per request and country, seeded with `seed_instance()`. Never `Faker.seed()` (it seeds one generator shared by all instances). Never Faker's `iban()` or `swift()`. Supported locales: GB, IE, US, DE, FR, IT, ES, NL, BE, PL, AT, PT, plus `ru_RU` for Exposures (section 8).
- **schwifty** for IBANs: `IBAN.random(cc, random=rng, bank_code=<Clean Bank List entry>, account_code=<numeric, generated by us>)`. The numeric `account_code` matters for FR, IT, CH and LU, whose formats otherwise admit random letters. For DE use `IBAN.random(..., bank_code=...)` rather than `IBAN.generate`, because the German check digit sits inside the account code. BICs come from the Clean Bank List entry, never from schwifty draws.
- **US accounts:** `Othr/Id` with an ABA routing number and account number; the agent BIC comes from the hand-maintained US entries.
- **Amounts and currencies** are built by our own seeded RNG with `Decimal` and a country-to-currency map (section 5.5). Faker's `currency_code()` is not used.

---

## 5. Generation: request model and Supplied Data merging

Source: [Request model and Supplied Data merging](https://github.com/Tryline-Studios/pain-demo/issues/8) with its amendment from [Sanctioned-country exposure in Generated Data](https://github.com/Tryline-Studios/pain-demo/issues/19); context from [Seeded fake payment data libraries](https://github.com/Tryline-Studios/pain-demo/issues/4) and [Seed contract across app upgrades](https://github.com/Tryline-Studios/pain-demo/issues/15).

### 5.1 Shape

One JSON object, snake_case throughout. It mirrors the file, so the same model serves the form, the API and the CSV.

```
message_version            enum, pain.001.001.03 .. .13; default pain.001.001.03
seed                       string, max 64 chars; optional (section 9.2)
created_at                 datetime; default now (GrpHdr/CreDtTm)
execution_date             date; default today (ReqdExctnDt)
message_id                 string; optional (GrpHdr/MsgId)
transaction_count          int, 1..100 (section 5.2)
countries[]                ISO 3166-1 alpha-2 from the twelve; default ["GB","DE","FR","NL","US"]
currencies[]               ISO 4217; optional
amount_min, amount_max     decimal, two places; default 10 and 50000
hit_count                  int, >= 0 (section 6)
hits[]                     named Hits (section 6.4)
placements[]               allowlist for drawn Hits (section 6.4)
name_variants[]            allowlist for drawn Hits (section 6.4)
exposure_countries[]       from RU, BY, IR, KP, SY, VE (section 8)
exposure_count             int, >= 0 (section 8)
payment:                   file-level Supplied Data
  { payment_information_id, debtor, debtor_agent, debtor_account }
transactions[]:            per-transaction Supplied Data
  { end_to_end_id, creditor, creditor_agent, creditor_account, amount, currency,
    ultimate_debtor, ultimate_creditor, intermediary_agents[0..2],
    remittance: { unstructured[], structured? } }

party:    { name, address, id, country_of_residence }
agent:    { bic, lei, name, address }
address:  { street, building_number, postcode, town, country_subdivision, country, lines[], ... }
          (the ... are the newer PostalAddress24/27 parts; see section 5.4)
account:  { iban } | { other_id, scheme }
```

Everything under `payment` and `transactions` is optional Supplied Data. Everything else is a generation setting. Ultimate Debtor is transaction-level only; there is no payment-level `ultimate_debtor` (section 10.3).

Transaction indices are **1-based** wherever they appear: `hits[].transaction`, the Answer Key, XPath positions and CSV rows.

### 5.2 Rows

- `transaction_count` defaults to the number of supplied transactions, or 10 when none are supplied.
- A count larger than the supplied rows pads with generated transactions. A count smaller than the rows is a validation error.
- The cap is 100, a code constant published as `maxItems: 100` in OpenAPI. It is not configurable.

### 5.3 Merging, field by field

- An **absent** field is generated from the Seed's per-transaction stream, so supplying one field never reshuffles the others (section 9.3).
- An explicit **`null`** means "leave the element out". It is allowed only where the schema makes the element optional: Ultimate parties, Intermediary Agents, LEI, address parts, structured remittance. It is a validation error for required elements such as creditor name or amount.
- A supplied Debtor address country overrides `countries[0]` as the Debtor's country.
- **Optional roles in clean transactions** appear at background rates drawn from the Seed, so that an Ultimate party or an intermediary is not a tell for a Hit: Ultimate Creditor 10%, Ultimate Debtor 5%, one Intermediary Agent 5%, structured remittance 15%. The rates are code constants.
- **Hits versus Supplied Data:** a Hit wins. It replaces the targeted party or agent, and the Answer Key records the supplied value it displaced (section 11.4). Default draws prefer transactions where the target field was not supplied and fall back to supplied ones only when there is no room. Supplied Data rows cannot name a catalogue Entity; a named Hit pinned to a transaction number is the one way to place one.

### 5.4 Validation of Supplied Data

Checked at request time; errors name the field with a dotted path (section 12.3):

- lengths (`Nm` is `Max140Text`; street and town are 70 characters before .12 and 140 from .12);
- BIC pattern for the chosen Message Version (strict `BICIdentifier` in .03 to .08, the looser Dec2014 pattern from .09);
- ISO 3166 country codes and ISO 4217 currency codes;
- IBAN checksums via schwifty; `Othr/Id` length;
- a supplied field the chosen Message Version lacks is a validation error naming the field and the version: `lei` before .09; the PostalAddress24 parts (building name, floor, post box, room, town location name, district name) before .09; the PostalAddress27 parts (care-of, unit number) before .12; street or town over 70 characters before .12.

Supplied Data addresses accept any ISO 3166 country. The twelve-country limit applies only to `countries`, i.e. to what the app generates by default.

The XSD is the backstop. Sample Files are always valid; there is no deliberately-broken-file mode. Drops with a warning (section 10.4) apply only to Generated Data, never to a value the user supplied.

### 5.5 Countries, currencies, amounts

- `countries` is a list drawn from the twelve Faker-supported countries: GB, IE, US, DE, FR, IT, ES, NL, BE, PL, AT, PT. Default `["GB", "DE", "FR", "NL", "US"]`. A country outside the twelve in `countries` is a validation error.
- The Debtor takes `countries[0]`. Creditors and their agents draw per transaction from the whole list.
- Currency defaults to the creditor country's currency: GBP for GB, USD for US, PLN for PL, EUR for the rest. If `currencies` is given, each transaction draws uniformly from it instead.
- Amounts are two-decimal values drawn between `amount_min` and `amount_max`, default 10 to 50,000.
- US accounts use `Othr/Id` with an ABA routing number (section 4.5).

### 5.6 CSV format

This replaces the charting-time note "CSV in the library's template format": pain001's `template.csv` is per-version example data for the flat pipeline we do not use, and its columns do not match what pain001 renders.

- Our own flat CSV, one row per transaction.
- Column names are the flattened field paths of the model: `creditor.name`, `creditor.address.country`, `creditor_account.iban`, `creditor_agent.bic`, `intermediary_agents.0.bic`, `amount`, `currency`, `end_to_end_id`, and so on. Dots separate levels; list positions are 0-based integers in the path.
- File-level fields (`payment.*`) come from the first row. Later rows must match or leave them blank.
- Unknown columns are a validation error.
- The CSV carries Supplied Data only. Generation settings and Hits travel as JSON alongside it (section 12.1, `POST /sample-files/csv`).

### 5.7 Effective Request

`created_at` and `execution_date` default to now and today, and `seed` to a generated value. The response returns the Effective Request: the request with every default resolved (seed, created_at, execution_date, transaction_count, countries, and every other defaulted field). Replaying the Effective Request on the same Generator Version reproduces the Sample File byte for byte. The Effective Request is embedded in the Answer Key (section 11.2), and goldens are stored with theirs.

---

## 6. Placement selection and overrides

Source: [Placement selection and overrides](https://github.com/Tryline-Studios/pain-demo/issues/9); context from [Placements and fields per Message Version](https://github.com/Tryline-Studios/pain-demo/issues/2) and [Generation path](https://github.com/Tryline-Studios/pain-demo/issues/13).

### 6.1 Placements and eligibility

Placement enum: `debtor`, `debtor_agent`, `creditor`, `creditor_agent`, `ultimate_debtor`, `ultimate_creditor`, `intermediary_agent_1`, `intermediary_agent_2`, `intermediary_agent_3`, `remittance`.

| Placement | Bank | Corporate | Individual |
|---|---|---|---|
| Debtor, Creditor, Ultimate Debtor, Ultimate Creditor | yes | yes | yes |
| Debtor Agent, Creditor Agent, Intermediary Agent 1 to 3 | yes | no | no |
| Remittance mention | yes | yes | yes |

Every Placement is available in every Message Version. There is no per-version fallback or skip. Roles outside this list (Initiating Party, agent `BrnchId`, garnishment parties) are not Placements.

### 6.2 File-level and transaction-level

A Sample File has one `PmtInf`, so **Debtor and Debtor Agent are file-level Placements**: at most one Sanctioned Entity in each per file, and a request naming two different Debtors is a validation error. All other Placements are per transaction. Ultimate Debtor is always placed at transaction level. Intermediary Agents are filled contiguously from 1: an Entity placed as Intermediary Agent 2 implies a generated clean Intermediary Agent 1.

### 6.3 What a Hit is

- Hit Count counts Placements. A file-level Placement touches every transaction but counts as one Hit.
- By default at most one Hit per transaction. Hits land on transaction numbers drawn uniformly without replacement from the Seed's placement stream. Each Hit draws a distinct Entity until the catalogue is exhausted.
- Hit Count is capped at the transaction count plus two; higher is a validation error.
- Hit Count 0 yields a clean file.

### 6.4 Named Hits, allowlists and validation

A request carries `hit_count` (the total) and an optional `hits[]` list. Each named Hit:

```
entity            catalogue id, required
placement         optional
name_variant      optional
transaction       optional, 1-based; ignored (must be absent) for file-level Placements
rendering_mode    optional, agents only: name_and_bic | bic_only | name_only
with_controller   optional bool, controlled Legal Entities only
```

- Anything not pinned is drawn.
- Named Hits count toward `hit_count`. More named Hits than the count is a validation error.
- Two named Hits may share a transaction number; this is the only way to stack Hits in one transaction.
- Request-level allowlists `placements[]` and `name_variants[]` constrain the drawn Hits only.
- Validation errors, each naming the Entity and the field: a Placement not eligible for the Entity Type; an unsupported Name Variant for that Entity (section 7.6); `bic_only` for a Bank without a catalogue BIC; a transaction number outside 1 to `transaction_count`; two different Debtors or Debtor Agents.

### 6.5 Default draws

All weights are code constants, drawn from the Seed's placement stream.

| Draw | Weights |
|---|---|
| Placement, Corporate or Individual | Creditor 35, remittance mention 25, Ultimate Creditor 15, Ultimate Debtor 15, Debtor 10 |
| Placement, Bank | Creditor Agent 40, Intermediary Agent 30, Debtor Agent 15, party roles 10, remittance mention 5 |
| Intermediary slot | 1: 60, 2: 30, 3: 10; lower slots filled with clean generated banks |
| Name Variant | exact 40, alias 25, fuzzed 20, transliteration 10, native script 5; restricted to the variants the Entity supports and renormalised |
| Agent rendering mode | `name_and_bic` only |
| Remittance element | `Ustrd` 70, `Strd/AddtlRmtInf` 15, `Strd/Invcr` or `Strd/Invcee` 15 |

A draw landing on a file-level Placement already taken is redrawn.

### 6.6 Agent rendering modes

- `name_and_bic` (default): `FinInstnId` carries the BIC, the name and the address.
- `bic_only`: no name, no Name Variant; tests BIC screening alone. Needs a catalogue BIC.
- `name_only`: name and address, no BIC; tests name screening without the BIC shortcut. A Bank with no catalogue BIC is always `name_only`.

### 6.7 Remittance mentions

- `Ustrd` and `Strd/AddtlRmtInf` embed the rendered name in a seeded sentence template, e.g. "Invoice 4471 payment to {name}". Both are `Max140Text`; a template result over 140 characters is redrawn.
- `Strd/Invcr` and `Strd/Invcee` take the bare name in their own `Nm`.
- `CdtrRefInf/Ref` (35 characters) is never used as a target.
- The Answer Key records the element used (section 11.3).

### 6.8 Control Relationships

Only on request: a named Hit with `with_controller: true` places the controlled Legal Entity as a party and its controller as the matching Ultimate party in the same transaction (Evraz PLC as Creditor, Roman Abramovich as Ultimate Creditor; Debtor pairs with Ultimate Debtor at transaction level). It counts as two Hits and the two are paired in the Answer Key. Default draws never pair.

### 6.9 Coherence around a Hit

- A sanctioned party's address comes from its Listing. Its account is clean and in that country.
- A sanctioned Bank as agent: the account it services is in the Bank's country, using the Bank's own bank code when schwifty's registry has it. The counterparty's name and address are drawn from the request's countries like any generated party (a German company with an account at Sberbank Moscow), so no Faker locale is needed for catalogue countries.
- The account element follows the country: IBAN where the IBAN registry has the country (Belarus, Iran, and all twelve default countries except the US); otherwise `Othr/Id` in a country-appropriate synthetic format (Russian 20-digit account numbers; US ABA routing plus account; plain numeric for North Korea, Syria, Venezuela).
- Everything not tied to a Hit comes from the Clean Bank List (section 4).

---

## 7. Name Variants

Source: [Name Variant rules](https://github.com/Tryline-Studios/pain-demo/issues/7).

Five Name Variants: `exact`, `alias`, `native_script`, `transliteration`, `fuzzed`. Each is a pure function of the Entity's catalogue names and the seeded RNG, so the same Seed always yields the same string. Every choice (which name, which scheme, which operations) is recorded in the Answer Key (section 11.3).

### 7.1 Exact

A primary name, verbatim including casing, from one of the Entity's Listings chosen by the RNG. For Sberbank that is either OFAC's `PUBLIC JOINT STOCK COMPANY SBERBANK OF RUSSIA` or the UK's `PJSC Sberbank (Public Joint-Stock Company Sberbank)`.

### 7.2 Alias

Any non-primary Latin-script listed name, verbatim: `aka`, `fka`, `nka` or UK `primary_variation`. All are strong; weak aliases never enter the catalogue. f.k.a. names are included, and the Answer Key's source type lets a miss on them be judged separately.

### 7.3 Native Script

A listed non-Latin name verbatim (e.g. `ПАО Сбербанк`). The XSD allows any UTF-8; SWIFT gateways do not, so this is a Screening Tool test, not a gateway test.

### 7.4 Transliteration

A romanisation generated from a listed Cyrillic name under a named scheme, deliberately not on any list.

- Library `iuliia`, pinned exactly. Schemes: a curated subset of six with distinct output: ICAO, BGN/PCGN, ISO 9, ALA-LC, Russian passport 2013, Wikipedia. The scheme is chosen by the RNG and recorded.
- If the result equals a listed Latin name case-insensitively, another scheme is drawn. If every scheme collides, the variant is impossible for that Entity.
- Cyrillic only in v1. Entities whose only non-Latin names are in another script (the roster has one Persian name) do not support transliteration.

### 7.5 Fuzzed

Starts from any Latin-script listed name (primary or alias; never a non-Latin name, never a transliteration), picked by the RNG and recorded as the base. Operations are a fixed, named catalogue; anything else is not a fuzz.

| Operation | Applies to | Example |
|---|---|---|
| `typo` (one substitution, transposition, deletion or insertion; never in a token's first two characters) | all | `Sberbank` to `Sbrebank` |
| `drop_legal_form` | Legal Entities | `Evraz PLC` to `Evraz` |
| `abbreviate_legal_form` / `expand_legal_form` | Legal Entities | `Public Joint Stock Company` to `PJSC` and back |
| `punctuation` (hyphen to space and back; drop quotes, brackets, dots, diacritics) | all | `Alfa-Bank` to `Alfa Bank` |
| `reorder_tokens` (surname first; legal form moved) | all | `Roman Abramovich` to `Abramovich Roman` |
| `drop_token` (patronymic or middle name; filler word such as "of") | all | `Roman Arkadyevich Abramovich` to `Roman Abramovich` |
| `initial` (given name to initial) | Individuals | `R. Abramovich` |
| `whitespace` (double or trailing space) | all | |

- Case changes are not a fuzz: every Screening Tool is case-insensitive.
- Budget: at most two operations per name, at most one `typo`, and the result must keep a Jaro-Winkler similarity of at least 0.85 to its base (`rapidfuzz`, pinned exactly) or the RNG redraws.
- One intensity in v1. Levels can be added later without changing the Answer Key.
- The legal-form dictionary is a code constant, not catalogue data.

### 7.6 General rules

- Candidate names over 140 characters (`Nm` is `Max140Text`) are never chosen. A fuzz result over 140 is redrawn.
- An Entity **supports** a variant when it has at least one candidate name for it: `exact` always; `alias` when it has a non-primary Latin name; `native_script` when it has a non-Latin name; `transliteration` when it has a Cyrillic name and at least one scheme does not collide; `fuzzed` always. `GET /entities` publishes the supported set per Entity (section 12.1).
- An explicit request for a variant the Entity cannot support is a validation error naming the Entity and the variant. When the app chooses variants itself it draws only from those the Entity supports. Never a silent fallback to `exact`.
- The Answer Key records, per placed name: Entity id, Name Variant, the rendered string as it appears in the XML, the source name (value, source type, script, Listing), the scheme for a transliteration, and the base name plus ordered operations for a fuzz.

---

## 8. Exposures

Source: [Sanctioned-country exposure in Generated Data](https://github.com/Tryline-Studios/pain-demo/issues/19).

### 8.1 What an Exposure is

A clean transaction whose creditor side is deliberately placed in a sanctioned or high-risk country, to test country-based screening. Exposures are neither Hits nor clean; the Answer Key lists them separately (section 11.5).

### 8.2 Request

- `exposure_countries[]`: from RU, BY, IR, KP, SY, VE (the catalogue's programmes). Currencies: RUB, BYN, IRR, KPW, SYP, VES. Published with their currencies by `GET /options`.
- `exposure_count`: the number of clean transactions with an exposed creditor side; explicit, like Hit Count.
- By default Exposures and Hits land on distinct transactions.

### 8.3 What an exposed transaction gets, on the creditor side

- A Latin-script name. RU and BY: Faker `ru_RU` person and company names romanised with `iuliia` under BGN/PCGN (`Sazonov Arseniy Dmitrievich`, `NPO Nekrasova`). IR, KP, SY, VE: a name from the request's ordinary locales, i.e. a foreign party at a local address, because Faker has no usable Latin output for those countries.
- An address with a city from a small curated list per country (code constants: Moscow, St Petersburg, Minsk, Tehran, Pyongyang, Damascus, Caracas and a few more per country) and the country code.
- A **synthetic** creditor agent: a generated bank name plus a BIC carrying the country code (positions 5 and 6) and `0` as the eighth character, the ISO test-BIC marker, so it can never collide with a real institution. No real bank is named because no safely clean local bank exists in these countries.
- An account in the country's format: IBAN for BY and IR via schwifty with a synthetic bank code; `Othr/Id` for RU, KP, SY, VE (section 6.9).
- The country's currency.

### 8.4 Screening

Romanised RU and BY names pass the same catalogue check as every generated party name (section 4.4) and are redrawn on a match.

---

## 9. Seed, randomness and Generator Version

Source: [Seed contract across app upgrades](https://github.com/Tryline-Studios/pain-demo/issues/15); context from [Generation path](https://github.com/Tryline-Studios/pain-demo/issues/13) and [Seeded fake payment data libraries](https://github.com/Tryline-Studios/pain-demo/issues/4).

### 9.1 The promise

Same request plus same Seed yields the byte-identical Sample File and Answer Key **within one Generator Version**. Across Generator Versions there is no promise; the Answer Key says which one produced it. "Same request" means the same Effective Request (section 5.7).

### 9.2 Seed format

An opaque string of at most 64 characters, so callers can write `regression-run-42`. When absent, the app generates 16 hex characters from the OS random source. The Seed is always echoed back, in the Effective Request, the Answer Key and the Sample File's leading XML comment.

### 9.3 Deriving randomness

- One master Seed feeds independent streams, each seeded from a hash of the Seed and a stable stream name: one Faker instance per country, schwifty draws, amounts, Placement selection, Name Variant choices, identifiers, Exposures.
- Each transaction has its own sub-stream keyed by its number, so transaction *i* is identical whether the file holds 10 or 100 transactions, and adding a Hit does not reshuffle the innocent rows.
- Redraws (name screening, fuzz budget, collisions) consume from the same stream they started in, so they stay deterministic.
- The rendering engine contributes no randomness: message id, payment information id and end-to-end ids are generated by our seeded RNG and passed explicitly (section 10.5).

### 9.4 Generator Version

The app version (semver from `pyproject.toml`) plus git SHA, together with the exact versions of `pain001`, `Faker`, `schwifty`, `iuliia` and `rapidfuzz`, and the Entity Catalogue snapshot date. The Answer Key records all of them explicitly; there is no opaque fingerprint. `GET /version` returns the same block.

Every Sample File starts with a one-line XML comment carrying the Seed and the app version, placed after the XML declaration and before the root element, so a file separated from its Answer Key still says where it came from. Comments are ignored by the XSD and by Screening Tools.

### 9.5 Goldens and upgrades

See section 15.3 and 15.4. Any commit that changes a golden also bumps the app's minor version, so "different app version" and "different output for the same Seed" mean the same thing.

---

## 10. Rendering engine and version fitting

Source: [Generation path: flat templates vs corpus.build](https://github.com/Tryline-Studios/pain-demo/issues/13), [Placements and fields per Message Version](https://github.com/Tryline-Studios/pain-demo/issues/2), ADR-0002.

### 10.1 Engine

`pain001.corpus.build(scenario, version)`, from `pain001[fast]` pinned exactly (the `fast` extra supplies lxml). It emits every Placement in every Message Version, renames `BIC`/`BICFI` per version, sorts children into schema order, is deterministic, and validates its output against the bundled XSD. The flat pipeline (`generate_xml_string` with the bundled per-version `template.xml`) is not used: it cannot emit Intermediary Agents in any version and emits only Debtor and Creditor names in .04 to .08.

### 10.2 Isolation seam

One renderer module holds every pain001 import. Input: our own resolved Sample File model. Output: XML bytes plus the build report. The request model, Placement logic and Answer Key never see pain001 types or its scenario schema. The `raw` element-merge escape hatch is not used in v1; a need for it becomes a ticket.

Generation is blocking and pain001 registers XML namespaces process-wide, so the renderer runs off the event loop (a worker thread).

### 10.3 ISO rules the XSD cannot express

Made unrepresentable in our model rather than checked after the fact:

- Ultimate Debtor is placed at transaction level only, never at payment level (the MDR forbids both).
- Intermediary Agents are filled contiguously from 1 (`IntrmyAgt2` requires `IntrmyAgt1`, `IntrmyAgt3` requires `IntrmyAgt2`).

pain001's `corpus.rules.mdr.evaluate_mdr` runs only in the test suite as a second opinion.

### 10.4 XSD validation and the build report

- XSD validation stays on for every request. A failure is a `500 build_failed` response (section 12.3), never a silently invalid file.
- If the version fitter dropped an element that carried a Placement, the request fails with `build_failed` (the Answer Key would otherwise be wrong).
- Every other drop (agent `LEI` before .09, PostalAddress24 or 27 parts in older versions) is returned as a warning in the Answer Key's `warnings` list. Warnings apply only to Generated Data; a supplied value the version lacks is rejected at validation instead (section 5.4).

### 10.5 What changes per Message Version

| Aspect | .03 | .04 to .08 | .09 to .11 | .12 to .13 |
|---|---|---|---|---|
| Agent BIC element | `BIC` (strict pattern) | `BICFI` (strict pattern) | `BICFI` (Dec2014 pattern) | `BICFI` (Dec2014 pattern) |
| Agent `LEI` | no | no | yes | yes |
| Address type | PostalAddress6 | PostalAddress6 | PostalAddress24 (adds building name, floor, post box, room, town location, district) | PostalAddress27 (adds care-of, unit number; street and town widen to 140) |
| Party and agent `Nm` | Max140Text | Max140Text | Max140Text | Max140Text |
| All Placement roles, `Ustrd` (unbounded), `Strd` with `Invcr`/`Invcee` and up to 3 `AddtlRmtInf` | yes | yes | yes | yes |

Identifiers (`MsgId`, `PmtInfId`, `EndToEndId`) come from our seeded RNG and are passed explicitly; corpus.build's `auto` identifiers are not used. `GrpHdr/InitgPty` is rendered as the Debtor.

---

## 11. Answer Key

Source: [Answer Key format](https://github.com/Tryline-Studios/pain-demo/issues/10) with amendments from [API contract](https://github.com/Tryline-Studios/pain-demo/issues/11) (`file.sha256`) and [Sanctioned-country exposure in Generated Data](https://github.com/Tryline-Studios/pain-demo/issues/19) (`exposures`).

### 11.1 Format

JSON is canonical, produced from a Pydantic model with a fixed key order and pretty-printed with 2-space indentation and a trailing newline, so golden Answer Keys diff cleanly. A CSV with one row per Hit is a projection of `hits` (columns in order: hit id, scope, transaction number, end-to-end id, entity id, entity type, lists, placement, element, rendering mode, name variant, rendered text, source value, source type, scheme, operations joined by `|`, BIC, origin, paired hit, XPath). The CSV is served by `POST /answer-keys/csv` and inside the zip download (section 12.2).

### 11.2 Top level

```
answer_key_version: 1          integer, bumped only on a breaking change to this structure
seed
message_version
generator: { app_version, git_sha, pain001, faker, schwifty, iuliia, rapidfuzz, catalogue_snapshot }
request: { ... }               the Effective Request, embedded so the Answer Key alone reproduces the file
file: { message_id, created_at, execution_date, transaction_count, hit_count, sha256 }
summary: { by_placement, by_name_variant, by_entity_type, by_list, by_exposure_country }
hits: [ ... ]
exposures: [ { transaction_number, end_to_end_id, country, currency,
               elements: [creditor_address | agent_bic | account, ...] } ]
transactions: [ { number, end_to_end_id, hit_ids: [] } ]   every transaction, with the ids of every Hit
                               that touches it, file-level ones included (section 6.3); a clean transaction
                               (no Hit touches it) has an empty list
warnings: [ ... ]              build-report drops for Generated Data
```

- `file.sha256` is the hash of the Sample File's XML bytes, so a saved file can be matched to its Answer Key and checked for alteration before it reaches the Screening Tool.
- The full `transactions` list lets a Screening Tool alert on a transaction with no hit ids be counted as a false positive. A file-level Hit (Debtor or Debtor Agent) touches every transaction, so while there is one no transaction is clean.
- Nothing the catalogue already holds (programmes, full Listing detail) is repeated.

### 11.3 Per Hit

```
id: "h1"                       scope: file | transaction
transaction_number             absent for scope: file
end_to_end_id                  absent for scope: file
xpath                          from the document root to the exact element, e.g.
                               /Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf[3]/Cdtr/Nm ;
                               file-level hits point into PmtInf
entity: { id, entity_type, listings: [ { list, entry_id } ] }
placement                      debtor | debtor_agent | creditor | creditor_agent | ultimate_debtor |
                               ultimate_creditor | intermediary_agent_1..3 | remittance
element                        remittance only: ustrd | addtl_rmt_inf | invcr | invcee
rendering_mode                 agents only: name_and_bic | bic_only | name_only
name: { variant, rendered, source: { value, type, script, listing }, scheme?, base?, operations?[] } | null
                               null for bic_only
bic: { value, source: listing | gleif } | null
lei: value | null
address_from_listing: entry_id | null
triggers: [ { kind: name | bic | lei, value, listed_on: [ofac_sdn, uk] } ]
origin: named | drawn
paired_with: hit id | null     with_controller pairs
displaced: { field, value } | null   the Supplied Data value this hit replaced
```

`triggers` says what a Screening Tool could match on and which lists actually carry it. The UK list has no BIC field, and a GLEIF-sourced BIC is on no list at all, so a `bic_only` Hit on such a BIC is expected to be missed by a list-driven tool, and the Answer Key says so.

### 11.4 Pointers and ordering

- Transaction numbers are 1-based everywhere, matching XPath positions and spreadsheet rows. Each transaction-level Hit carries three coordinates: `transaction_number`, `end_to_end_id` and `xpath`.
- Hits are ordered file-level first, then by transaction number, then by XPath. Ids `h1`, `h2`, ... follow that order.
- `displaced` records the supplied value a Hit replaced (section 5.3).

### 11.5 Exposures

`exposures` lists each exposed transaction (section 8). Exposures never count toward Hit Count and never appear in `hits`. `summary.by_exposure_country` counts them.

---

## 12. API contract

Source: [API contract](https://github.com/Tryline-Studios/pain-demo/issues/11) with its amendment from [Sanctioned-country exposure in Generated Data](https://github.com/Tryline-Studios/pain-demo/issues/19); ADR-0001.

### 12.1 Endpoints under `/api/v1`

Resource nouns; nothing is stored, the response is the resource.

| Method and path | operationId | Purpose |
|---|---|---|
| `POST /sample-files` | `generate_sample_file` | Generate from a JSON request (section 5). Returns the Sample File plus Answer Key. |
| `POST /sample-files/csv` | `generate_sample_file_from_csv` | Same, as multipart: a `request` JSON part (generation settings and Hits) plus a `supplied_data` CSV file (section 5.6). |
| `POST /answer-keys/csv` | `answer_key_to_csv` | Pure transform: an Answer Key JSON in, the CSV projection of its hits out. |
| `GET /message-versions` | `list_message_versions` | The eleven Message Versions, default flagged. |
| `GET /entities` | `list_entities` | Catalogue listing: id, Entity Type, display name (first primary), lists, countries, supported Name Variants, supported Placements, has BIC. Filters `entity_type`, `list`, `country`. No pagination. |
| `GET /entities/{id}` | `get_entity` | Detail: every name with source, Listings, BICs, LEIs, addresses, Control Relationships. Individuals expose only what the catalogue holds. |
| `GET /options` | `get_options` | Supported countries with currency, exposure countries with currency, Placements, Name Variants, rendering modes, limits (max transactions) and defaults, so the UI hardcodes nothing. |
| `GET /version` | `get_version` | The Generator Version block (section 9.4). |
| `GET /health` | `get_health` | Compose healthcheck. |
| `POST /validations` | `validate_message` | Validate an Uploaded Message, as a multipart `file` or a raw `application/xml` body. Returns a Validation Report (section 17). |

Tags: `sample-files`, `catalogue`, `meta`, `validation`. Named operationIds beyond the two given in the ticket (`generate_sample_file`, `list_entities`) follow the same snake_case convention and are fixed at implementation.

### 12.2 Responses

Default JSON envelope for the generate endpoints:

```
{ "sample_file": { "filename": "<name>.xml", "content_type": "application/xml", "xml": "<string>" },
  "answer_key": { ... } }
```

- `?format=zip` on either generate endpoint returns a zip of `<name>.xml`, `<name>.answer-key.json` and `<name>.answer-key.csv`.
- `<name>` is `<message_version>-<seed>` with the seed reduced to `[A-Za-z0-9._-]`; anything else is hashed.
- Multipart responses are ruled out. The Answer Key embeds the Effective Request, so there is no third part.
- Every response carries `X-Request-Id` (section 14.2).

### 12.3 Errors

RFC 9457 Problem Details (`application/problem+json`) everywhere, overriding FastAPI's default 422 body. `instance` carries the request id.

| Status | `type` | When |
|---|---|---|
| 422 | `validation_error` | `errors: [{ field, message, code }]`, `field` a dotted path matching the request model (`hits[2].name_variant`, `transactions[3].creditor.name`). Covers the 100-transaction cap, impossible Entity/variant/Placement combinations, two Debtors, more named Hits than `hit_count`, Hit Count over transactions plus two, `transaction_count` below the supplied rows, unknown CSV columns, and version-lacking supplied fields (the message names the version). |
| 413 | | request body over 1 MB (10 MB on `POST /validations`) |
| 415 | | `POST /validations` with a content type other than multipart or `application/xml` |
| 500 | `build_failed` | the renderer's own output fails the XSD or drops a Placement; `detail` carries the XSD messages |

Build warnings for Generated Data are not errors; they ride in the Answer Key's `warnings`.

### 12.4 Limits

- At most 100 transactions per Sample File (`maxItems: 100` in OpenAPI; code constant).
- Hit Count at most `transaction_count + 2`.
- Request bodies at most 1 MB, except `POST /validations` at 10 MB.
- Seed at most 64 characters.

### 12.5 OpenAPI and versioning

- The path prefix is the version. Additive changes stay in `/api/v1`; breaking changes go to `/api/v2`.
- `backend/openapi.json` is committed, regenerated by `just openapi`, drift-checked in CI, and feeds the openapi-typescript client (`just gen-client`).
- `info.version` is the app semver.
- Stable snake_case operationIds; tags `sample-files`, `catalogue`, `meta`, `validation`.

---

## 13. Web UI

Source: [UI flow](https://github.com/Tryline-Studios/pain-demo/issues/12); context from [Repo layout, docker-compose and tooling](https://github.com/Tryline-Studios/pain-demo/issues/5) and [API contract](https://github.com/Tryline-Studios/pain-demo/issues/11).

### 13.1 Layout: the Workbench

One screen, no client-side router. A Generate | Validate toggle at the top switches between generation (this section) and Upload Validation (section 17.9). A settings pane on the left with three collapsible sections (File, Data, Hits) and a sticky Generate button; the output on the right. The settings pane opens at 560px and is resizable by a drag handle between the panes (380px to 900px, remembered per browser via `localStorage`). Spacing is generous: wide gaps between fields, tall rows for named Hits.

Prototype (throwaway, never merged): https://claude.ai/artifact/N5sTHZfmtRV7xch54Bjfjr, source on branch `prototype/ui-flow` at `frontend/prototype/ui-flow.html`. Variant B won; A (a wizard) lost on speed for repeat use, C (a transaction ledger) lost on discoverability of file-level settings, though its "click a cell to place a hit" idea could return as an alternative Hits editor.

### 13.2 Sections

- **File:** Message Version (default .03), transaction count (1 to 100), Seed (empty means the app generates and echoes one), country chips (first is the Debtor's), amount range, optional currency chips, exposure countries and count.
- **Data:** radio cards for Generated only / Supply some fields / Upload CSV. Supplied fields are grouped as payment level (one per file) and transactions. Optional elements use a tri-state control Generate / Leave out / Supply, which is the absent-versus-null distinction of section 5.3. The CSV card shows the flattened-field-path header.
- **Hits:** Hit Count, then one row per named Hit with Entity (grouped by type), Placement (ineligible ones disabled for that Entity Type; file-level ones marked), Name Variant (unsupported ones disabled), transaction number (disabled for file-level), and either a rendering mode for agents or an "add controller as Ultimate party" checkbox for a controlled Entity. Allowlist chips for Placements and Name Variants constrain the drawn Hits.

### 13.3 Output

Summary tiles (transactions, hits, echoed Seed, version), download buttons (zip, XML, Answer Key JSON, Answer Key CSV), then tabs with the **Answer Key table as the default**, the Sample File XML (hits highlighted) and warnings. Before the first generate, an empty state. A 422 renders as a problem block and as inline field errors on the rows the dotted paths point at.

### 13.4 Data flow

The form is populated from `GET /options`, `GET /message-versions` and `GET /entities` (supported Name Variants and Placements per Entity drive the disabled options). It posts to `POST /sample-files` or `POST /sample-files/csv`, renders the JSON envelope, and downloads via `?format=zip`. The UI uses only the public API through the generated client (`openapi-fetch`, `openapi-react-query`).

---

## 14. Observability

Source: [Observability: request logging and error reporting](https://github.com/Tryline-Studios/pain-demo/issues/17).

### 14.1 Format

Structured logs via `structlog` (ordinary pin, Dependabot allowed). JSON lines in the container, coloured console lines in the native dev loop, chosen by `PAIN_DEMO_LOG_FORMAT=json|console`, defaulting to console when stdout is a TTY and JSON otherwise.

### 14.2 Request id

Accept an incoming `X-Request-Id` (kept when it is 1 to 128 characters of `[A-Za-z0-9._:-]`, otherwise replaced) or generate a UUID. Echo it as a response header, put it in the problem details `instance` on every error, and bind it to every log line of that request.

### 14.3 One event per request

At INFO: request id, method, path, status, duration in ms. Generate calls add Message Version, transaction count, Hit Count, named-Hit count, data source (`generated`, `form`, `csv`), Seed as echoed, warning count and outcome (`generated`, `validation_error`, `build_failed`). Never the request body, Supplied Data, generated names or the XML. Validation calls add the fields in section 17.7. Health checks log at DEBUG.

### 14.4 Build failures

`500 build_failed` is our bug by construction. It logs at ERROR with the request id, the XSD messages and the full Effective Request as JSON, Supplied Data included, so a maintainer can replay it exactly. This is the only place a request body is logged. The response carries the request id and the XSD messages, not the Effective Request.

### 14.5 Plumbing

- uvicorn's access log is disabled; its error logger routes through the same structlog pipeline.
- `PAIN_DEMO_LOG_LEVEL` defaults to INFO. DEBUG adds the scenario dict handed to corpus.build and its build report per request.
- Caddy keeps its default JSON access log to stdout.
- Startup validation failures (Entity Catalogue, Clean Bank List) log at CRITICAL and exit non-zero, which the compose healthcheck surfaces.

---

## 15. Testing, CI and upgrade procedures

Source: [Repo layout, docker-compose and tooling](https://github.com/Tryline-Studios/pain-demo/issues/5), [Seed contract across app upgrades](https://github.com/Tryline-Studios/pain-demo/issues/15), [Keeping Generated Data free of unplanned hits](https://github.com/Tryline-Studios/pain-demo/issues/14), [Entity Catalogue contents and schema](https://github.com/Tryline-Studios/pain-demo/issues/6), [Generation path](https://github.com/Tryline-Studios/pain-demo/issues/13).

### 15.1 Backend tests

- pytest unit tests for the pure domain logic (Placement selection, Name Variants, RNG derivation, merging).
- In-process API tests via FastAPI's test client.
- A shared helper validates every XML produced in any test against its Message Version's XSD.
- Hypothesis property tests: any valid request in any Message Version yields XSD-valid XML whose Answer Key matches the file.
- `evaluate_mdr` from pain001 runs over generated files as a second opinion on the MDR rules.
- The Clean Bank List assertion (no BIC or normalised name shared with the Entity Catalogue) runs as a test.
- No coverage threshold.

### 15.2 Frontend tests

- Vitest, React Testing Library and MSW.
- One Playwright smoke test against the compose stack: generate a file, then download it.

### 15.3 Goldens

Two fixed requests rendered in all eleven Message Versions, Sample File and Answer Key both committed under the backend tests (44 files), each stored with its Effective Request (embedded in the Answer Key):

- a clean file: Hit Count 0, Generated Data only;
- a kitchen sink: every Placement, every Name Variant, partial Supplied Data, several countries and currencies (and, by extension of the Exposure decision, at least one Exposure).

CI byte-compares them, and uploads each Sample File to `POST /validations`, which must report it valid (section 17.8).

### 15.4 Upgrade procedures

| Recipe | What it does | Where it runs |
|---|---|---|
| `just upgrade-generators` | bumps whichever named pins among `pain001`, `Faker`, `schwifty`, `iuliia`, `rapidfuzz`, regenerates the goldens and shows the diff for review | by hand |
| `just verify-catalogue` | downloads the current OFAC SDN and UK Sanctions List files and reports catalogue drift: delisted, renamed, BIC changed. Imports nothing. | by hand, never CI |
| `just verify-clean-banks` | checks every Clean Bank List entry by name and BIC against the current OFAC SDN and UK Sanctions List files and reports matches. Imports nothing. | by hand, never CI |
| `just build-clean-banks` | rebuilds the Clean Bank List from the pinned schwifty registry minus catalogue matches; a human reviews the diff | by hand |
| `just openapi` | regenerates `backend/openapi.json` from the app | by hand; CI checks drift |
| `just gen-client` | regenerates the TypeScript client from `openapi.json` | by hand; CI checks drift |

A catalogue edit or a Clean Bank List edit goes through the same golden regeneration as a pin bump. Any commit that changes a golden bumps the app's minor version.

### 15.5 CI and hooks

- GitHub Actions, parallel jobs: ruff, ty, pytest (including goldens and the Clean Bank List assertion); Biome, `tsc`, Vitest; client and `openapi.json` drift checks; both image builds, then the Playwright smoke test.
- `prek` pre-commit hooks run formatters and linters only.
- Dependabot, grouped: tooling and frameworks only. `pain001`, `Faker`, `schwifty`, `iuliia` and `rapidfuzz` are excluded and upgraded deliberately.

---

## 16. Configuration

Source: [Repo layout, docker-compose and tooling](https://github.com/Tryline-Studios/pain-demo/issues/5), [Observability](https://github.com/Tryline-Studios/pain-demo/issues/17).

`pydantic-settings` with the `PAIN_DEMO_` prefix, plus a committed `.env.example`. No secrets.

| Setting | Default | Meaning |
|---|---|---|
| `PAIN_DEMO_LOG_FORMAT` | `console` when stdout is a TTY, else `json` | log renderer |
| `PAIN_DEMO_LOG_LEVEL` | `INFO` | `DEBUG` adds the corpus.build scenario and build report per request |
| `PAIN_DEMO_GIT_SHA` | the checkout's `HEAD`, else `unknown` | the commit reported in the Generator Version; the image build sets it because the container has no `.git` (added by the walking-skeleton ticket, [#23](https://github.com/Tryline-Studios/pain-demo/issues/23)) |

Not configurable (code constants): the 100-transaction cap; the default countries, amount range and currencies; Placement, Name Variant, intermediary slot and remittance element weights; the background rates for optional roles; the fuzz budget and the 0.85 similarity threshold; the transliteration scheme set; the legal-form dictionary; the Exposure city lists; the 1 MB body limit; the 10 MB Upload Validation limit, the 500,000-element limit and the 100-problem cap.

---

## 17. Upload Validation

Source: [Upload Validation: scope, error report and API](https://github.com/Tryline-Studios/pain-demo/issues/64). Added when the map's destination was redrawn on 2026-11-12; it is the first feature implemented.

A user uploads an Uploaded Message (a pain.001 XML document this app did not necessarily produce) and gets back a Validation Report: valid, or every Validation Problem with what is wrong, the element, the line and the cause.

### 17.1 Endpoint

`POST /api/v1/validations`, operationId `validate_message`, tag `validation`. It accepts either:

- `multipart/form-data` with one `file` part, or
- a raw body with `Content-Type: application/xml` (for `curl --data-binary @file.xml`); `file.name` is then null.

Any other content type is a 415 problem; a missing or empty file is a 422 `validation_error`; a body over 10 MB is a 413. Validation is blocking and runs off the event loop, like the renderer.

### 17.2 Response: always 200 with a Validation Report

An invalid Uploaded Message is the expected outcome of asking "is this valid?", not a bad request, so it is a 200, never a 4xx. Problem details stay for broken requests only.

```
{ "valid": false,
  "message_version": "pain.001.001.03",   // null if not detected
  "encoding": "UTF-8",
  "transaction_count": 12,                // number of CdtTrfTxInf; null until the XSD layer ran
  "file": { "name": "batch.xml", "size_bytes": 48211, "sha256": "<hex>" },
  "problems": [ ... ],                    // document order
  "truncated": false }
```

`valid` is true exactly when `problems` is empty.

### 17.3 Checks, in layers

Each layer runs only if the previous one passed, so a malformed file reports one problem, its first parse error.

1. **Well-formed XML.** Parsed with lxml hardened for untrusted input: no entity resolution, no network, no DTD loading, no huge-tree mode. Any encoding the XML declaration names and lxml supports is accepted; with no declaration, UTF-8 (a BOM is fine). Undecodable bytes are `malformed_xml`.
2. **No DTD.** Any `<!DOCTYPE>` is `dtd_not_allowed`. Real pain.001 never carries one.
3. **Supported message.** The root `Document` namespace must be `urn:iso:std:iso:20022:tech:xsd:pain.001.001.NN` for one of the eleven Message Versions (.03 to .13), which sets `message_version`. Anything else is `unsupported_message`, naming the namespace found.
4. **At most 500,000 elements.** More is `too_many_elements`, naming the count and the limit ([#70](https://github.com/Tryline-Studios/pain-demo/issues/70)). The richest realistic 10 MB pain.001 (every optional element, minimum-length values, no indentation) has about 400,000; a flood of empty elements reaches 1.3 million. The XSD cost grows with errors times each error's position among its siblings, so a hostile file under the limit can still run for minutes or longer. Measured with empty `Ustrd` siblings under one parent: 40,000 took 1.5 s and 120,000 took 12.6 s on an idle Apple M3 Pro (close to the square of the count); under CPU load, 40,000 took 21 s and 240,000 about 240 s. A file at the limit is not measured and may take far more than minutes. It holds its own worker thread, and while it runs it slows every other thread (section 17.4); the follow-up ticket adds a time budget.
5. **XSD-valid** against that Message Version's schema. All errors are collected in one pass.

Rules beyond the XSD (MDR or CBPR+ usage rules, IBAN checksums, `NbOfTxs` and `CtrlSum` consistency) are not checked yet; see section 17.9.

### 17.4 Schemas

The XSDs are pain001's bundled schemas for .03 to .13, the same ones the renderer validates against (section 10.4), so what we validate cannot drift from what we generate. The renderer module stays the only pain001 import and also exposes the compiled schema per Message Version; schemas are compiled once per worker thread and reused, so concurrent validations never wait for each other on a shared schema (an lxml schema's error log belongs to the schema, not the call). They still share the GIL: lxml takes it once per XSD error, so while one upload is producing tens of thousands of errors every other request slows down without stopping (beside 50,000 errors, a one-transaction upload took 0.5 to 1.7 s instead of milliseconds, whether or not its thread had already compiled the schema). `docs/xsd/` is not committed (the example `.03` file supplied for this feature is identical to the bundled one apart from whitespace).

### 17.5 Validation Problem

```
{ "line": 42, "column": 18,
  "tag": "BIC",
  "path": "/Document/CstmrCdtTrfInitn/PmtInf[1]/CdtTrfTxInf[3]/CdtrAgt/FinInstnId/BIC",
  "code": "pattern_mismatch",
  "cause": "<lxml's raw message>",
  "message": "BIC 'ABCD12' on line 42 doesn't match the pattern [A-Z]{6}[A-Z2-9][A-NP-Z0-9]([A-Z0-9]{3}){0,1}" }
```

- `path` is an XPath of local names with 1-based positions, no namespace prefixes; null for `malformed_xml`.
- `tag` is the element's local name; null where there is no element.
- `cause` is the parser's text, kept for experts; `message` is our own sentence built from `code` and the values the parser gives (element, value, pattern, expected elements, length limit).
- `code` is a closed enum in OpenAPI: `malformed_xml`, `dtd_not_allowed`, `unsupported_message`, `too_many_elements`, `missing_element`, `unexpected_element`, `pattern_mismatch`, `invalid_value`, `too_long`, `too_short`, and the catch-all `schema_violation` (message falls back to `cause`). Adding a code is an additive change.

### 17.6 Ordering and cap

Problems come in document order, at most 100; beyond that `truncated` is true. Later XSD errors can be knock-on effects of an earlier one; they are reported anyway.

### 17.7 Logging

The one INFO event per request (section 14.3) adds `message_version`, `valid`, problem count, the distinct problem codes, `size_bytes` and `sha256`. Never the file content, element values or names: an Uploaded Message may hold real customer data.

### 17.8 Testing

- pytest through the HTTP seam: one fixture per layer and per code, at least one per Message Version, the raw and multipart paths, 413, 415, the 100-problem cap, just over and at the element limit, and two validations of the same Message Version running concurrently.
- Round trip: every golden Sample File (section 15.3) is uploaded and must come back valid.
- An XXE and an entity-expansion fixture prove the parser hardening.

### 17.9 Workbench

Source: [Upload Validation in the Workbench](https://github.com/Tryline-Studios/pain-demo/issues/71).

- **Mode switch.** A Generate | Validate toggle at the top of the Workbench. Generate is the screen of section 13. Validate keeps the same two panes and swaps their content.
- **Input (left pane).** A drop zone that also opens a file picker (`.xml`, up to 10 MB), and a paste box with a "Validate pasted XML" button. A file is sent as multipart so its name is reported; pasted XML is sent as a raw `application/xml` body.
- **Report (right pane).** Summary tiles: verdict, Message Version, transactions, problem count (`100+` when `truncated`) and encoding, then the file name, size and a short sha256. Below them, the Uploaded Message's source with line numbers: lines with a Validation Problem are highlighted and its `code` and `message` appear inline under the line. A problem rail on the right lists every problem with `code`, line, `message`, and the `path` and raw `cause`; clicking one scrolls the source to its line. Problems with no line (such as a `dtd_not_allowed` without one) appear in the rail only. A valid message shows "No problems found".
- **Large files.** The source view is virtualised, rendering only the visible lines, so a 10 MB message shows every line. Whether that is a small dependency or a hand-rolled windowed list is left to the build ticket.
- **Request problems.** A 413, 415 or 422 is shown as a problem block in the report area, like a 422 in section 13.3.
- **From a generated Sample File.** Generate mode gains a "Validate this Sample File" action that switches to Validate with the generated XML loaded. It is built once generation exists.

Prototype (throwaway, never merged): branch `prototype/upload-validation`, folder `frontend/src/workbench/prototype-validation/`. Variant A (the mode switch with tiles and a table) won, with B's source inspector replacing A's table. C (a tab of the output pane with problems grouped by code) lost.

Rules beyond the XSD are out of scope: the Screening Tool validates against the pain.001.001.03 XSD, and its one known rejection (`DbtrAcct/Tp/Cd` set to `SAVING` instead of `SVGS`) is an XSD enumeration error this section already reports as `invalid_value`.

---

## Appendix A: ADR index

| ADR | Decision |
|---|---|
| [ADR-0001](adr/0001-own-api-over-bundled-pain001-api.md) | Own REST API (`/api/v1`) instead of pain001's bundled API; pain001 pinned exactly as an internal dependency |
| [ADR-0002](adr/0002-corpus-build-over-flat-templates.md) | `pain001.corpus.build` over the flat template pipeline; one renderer module; goldens guard the pin |

Every other ticket explicitly declined an ADR.

## Appendix B: Ticket index

| Section | Source tickets |
|---|---|
| 1 Purpose and scope | [Map](https://github.com/Tryline-Studios/pain-demo/issues/1); out-of-scope lines from [#6](https://github.com/Tryline-Studios/pain-demo/issues/6), [#9](https://github.com/Tryline-Studios/pain-demo/issues/9), [#17](https://github.com/Tryline-Studios/pain-demo/issues/17), [#18](https://github.com/Tryline-Studios/pain-demo/issues/18), [#20](https://github.com/Tryline-Studios/pain-demo/issues/20) |
| 2 Architecture and repo layout | [Repo layout, docker-compose and tooling](https://github.com/Tryline-Studios/pain-demo/issues/5), [Generation path](https://github.com/Tryline-Studios/pain-demo/issues/13), ADR-0001, ADR-0002 |
| 3 Entity Catalogue | [Entity Catalogue contents and schema](https://github.com/Tryline-Studios/pain-demo/issues/6), [Entity Catalogue candidate roster](https://github.com/Tryline-Studios/pain-demo/issues/16), [Sanctions list entry shape](https://github.com/Tryline-Studios/pain-demo/issues/3) |
| 4 Clean Bank List and screening | [Keeping Generated Data free of unplanned hits](https://github.com/Tryline-Studios/pain-demo/issues/14), [Seeded fake payment data libraries](https://github.com/Tryline-Studios/pain-demo/issues/4) |
| 5 Request model | [Request model and Supplied Data merging](https://github.com/Tryline-Studios/pain-demo/issues/8), amendment from [#19](https://github.com/Tryline-Studios/pain-demo/issues/19) |
| 6 Placement selection | [Placement selection and overrides](https://github.com/Tryline-Studios/pain-demo/issues/9), [Placements and fields per Message Version](https://github.com/Tryline-Studios/pain-demo/issues/2) |
| 7 Name Variants | [Name Variant rules](https://github.com/Tryline-Studios/pain-demo/issues/7) |
| 8 Exposures | [Sanctioned-country exposure in Generated Data](https://github.com/Tryline-Studios/pain-demo/issues/19) |
| 9 Seed and Generator Version | [Seed contract across app upgrades](https://github.com/Tryline-Studios/pain-demo/issues/15) |
| 10 Rendering engine | [Generation path: flat templates vs corpus.build](https://github.com/Tryline-Studios/pain-demo/issues/13), [Placements and fields per Message Version](https://github.com/Tryline-Studios/pain-demo/issues/2), ADR-0002 |
| 11 Answer Key | [Answer Key format](https://github.com/Tryline-Studios/pain-demo/issues/10), amendments from [#11](https://github.com/Tryline-Studios/pain-demo/issues/11) and [#19](https://github.com/Tryline-Studios/pain-demo/issues/19) |
| 12 API contract | [API contract](https://github.com/Tryline-Studios/pain-demo/issues/11), amendment from [#19](https://github.com/Tryline-Studios/pain-demo/issues/19), ADR-0001 |
| 13 Web UI | [UI flow](https://github.com/Tryline-Studios/pain-demo/issues/12) |
| 14 Observability | [Observability: request logging and error reporting](https://github.com/Tryline-Studios/pain-demo/issues/17) |
| 15 Testing and upgrades | [#5](https://github.com/Tryline-Studios/pain-demo/issues/5), [#15](https://github.com/Tryline-Studios/pain-demo/issues/15), [#14](https://github.com/Tryline-Studios/pain-demo/issues/14), [#6](https://github.com/Tryline-Studios/pain-demo/issues/6), [#13](https://github.com/Tryline-Studios/pain-demo/issues/13) |
| 16 Configuration | [#5](https://github.com/Tryline-Studios/pain-demo/issues/5), [#17](https://github.com/Tryline-Studios/pain-demo/issues/17) |
| 17 Upload Validation | [Upload Validation: scope, error report and API](https://github.com/Tryline-Studios/pain-demo/issues/64), [Upload Validation in the Workbench](https://github.com/Tryline-Studios/pain-demo/issues/71) |

Research branches (primary sources, never merged): `research/placements-per-message-version`, `research/seeded-fake-payment-data`, `research/sanctions-list-entry-shape`, `research/entity-catalogue-roster`. Prototype branch: `prototype/ui-flow`.

## Open points found while assembling

All eight were reviewed and accepted as written on 2026-09-17 (see the resolution on [Assemble docs/spec.md](https://github.com/Tryline-Studios/pain-demo/issues/21)); the choices below are decisions, not questions. None blocks implementation.

1. **Golden count.** [Generation path](https://github.com/Tryline-Studios/pain-demo/issues/13) says "One fixed Seed rendered in all eleven Message Versions is committed and byte-compared in CI." The later [Seed contract across app upgrades](https://github.com/Tryline-Studios/pain-demo/issues/15) says "two fixed requests rendered in all eleven Message Versions ... (44 files)". This spec follows the later ticket (section 15.3).

2. **ADR-0001 names the wrong pain001 function.** ADR-0001 reads "call pain001's in-memory functions (e.g. `generate_xml_string`) as a pinned internal dependency", while ADR-0002 and [Generation path](https://github.com/Tryline-Studios/pain-demo/issues/13) settle on `corpus.build` and say the flat pipeline "is not used". The decision in ADR-0001 (own API, bundled API not mounted) stands; only its example is stale. Suggested follow-up: amend the example in ADR-0001 to "e.g. `pain001.corpus.build`, see ADR-0002". **Fixed on this branch:** the example now reads `pain001.corpus.build`, see ADR-0002.
3. **Two client-generation recipes.** [Repo layout](https://github.com/Tryline-Studios/pain-demo/issues/5) names `just gen-client`; [API contract](https://github.com/Tryline-Studios/pain-demo/issues/11) names `just openapi` for regenerating `openapi.json`. This spec treats them as two steps (section 15.4): `openapi` writes the JSON, `gen-client` writes the TypeScript client. Two recipes, two steps.

4. **Currency override versus Exposures.** [Request model](https://github.com/Tryline-Studios/pain-demo/issues/8) says that when `currencies` is given "each transaction draws uniformly from it". [Sanctioned-country exposure](https://github.com/Tryline-Studios/pain-demo/issues/19) says an exposed transaction gets "the country's currency". Neither ticket says which wins when both apply. This spec follows the later ticket for exposed transactions (the Exposure currency applies) and the `currencies` list for all others.

5. **`GET /health` and `GET /version` bodies.** [API contract](https://github.com/Tryline-Studios/pain-demo/issues/11) fixes `/version` to "the Generator Version block" and `/health` to "Compose healthcheck" without a body. The implementer should return `{ "status": "ok" }` from `/health` and exactly the Answer Key's `generator` block (section 11.2) from `/version`, so the two stay in sync.

6. **Address fields in Supplied Data for exposure countries.** [Request model](https://github.com/Tryline-Studios/pain-demo/issues/8) says "A country outside the twelve is a validation error" and its amendment from [#19](https://github.com/Tryline-Studios/pain-demo/issues/19) says "Supplied Data addresses accept any ISO 3166 country". This spec reads the first as applying to `countries[]` only (section 5.4 and 5.5), which is what the amendment states.

7. **Kitchen-sink golden and Exposures.** The kitchen-sink golden was defined in [Seed contract](https://github.com/Tryline-Studios/pain-demo/issues/15) before Exposures existed. This spec adds "at least one Exposure" to it (section 15.3) so the exposures path is covered by goldens; this was an inference at assembly time and is now accepted.

8. **Configuration surface.** Only two `PAIN_DEMO_` settings are named by any ticket (section 16). Host and port for uvicorn, and any Caddy settings, are left to compose and the FastAPI defaults; no ticket asked for more.

Added while building [Drawn Hits on party and agent Placements](https://github.com/Tryline-Studios/pain-demo/issues/30):

9. **Sanctioned Debtor beside a sanctioned Debtor Agent.** Both own the one `DbtrAcct` (section 6.9). The Debtor Agent's Entity is then a Bank in the Debtor's Listing country, drawn from the placement stream; if no such Bank is free, the Debtor's rule wins (its account is clean and in its own country) and the agent still renders its name and BIC.
10. **Sanctioned Creditor outside the request's countries.** Its account is in its Listing country (section 6.9), but its Creditor Agent is a clean bank from the request's countries, so e.g. Alrosa holds a Russian `Othr/Id` at a US bank. Known limit: synthetic agents for sanctioned countries arrive with Exposures ([#37](https://github.com/Tryline-Studios/pain-demo/issues/37)).
