# pain-demo

Validates and generates **ISO 20022 pain.001** (Customer Credit Transfer Initiation) files for testing and proving a sanctions payment Screening Tool.

- **Validate** an Uploaded Message: any pain.001 file, from this app or not, checked against its Message Version's XSD, with every Validation Problem explained in plain language.
- **Generate** a Sample File: fake payment data (or data you supply) mixed with real Sanctioned Entities from the OFAC SDN List and the UK Sanctions List, such as Sberbank and Evraz PLC, together with an Answer Key that says exactly what the Screening Tool should flag.

Both run in the **Workbench**, a single-screen web UI that opens in Validate mode, and over a REST API at `/api/v1`, which scripts and CI can call directly. Validation also runs from the command line (`pain validate`) without Docker or a server.

> **Status:** v1 is built: Upload Validation, Sample File generation and the Workbench all work. The build-ready spec is [`docs/spec.md`](docs/spec.md). New work is tracked as GitHub issues labelled `ready-for-agent`, and the design history is on the issue labelled `wayfinder:map` ([#1](https://github.com/Tryline-Studios/pain-demo/issues/1)).

## Just run it

All you need is Docker (Docker Desktop on Windows or macOS). Both images build inside Docker, so you don't need Python, Node or `just`. From the repo root:

```sh
docker compose up --build --detach --wait
```

Then open http://localhost:8080. Stop it with `docker compose down`.

- The first build downloads base images and packages from Docker Hub, ghcr.io, PyPI and npm. A TLS-inspecting corporate proxy can make that fail.
- On a virtual PC, Docker Desktop needs nested virtualisation turned on in the hypervisor.
- Run this way, the version shows the git SHA as `unknown`, because only `just up` passes it in. Nothing else changes.

To validate files only, you don't need Docker at all: see [Validate from the command line](#validate-from-the-command-line).

## What it does

### Upload Validation

`POST /api/v1/validations` takes a pain.001 file as a multipart `file` part, or as a raw `application/xml` body:

```sh
curl --data-binary @batch.xml -H 'Content-Type: application/xml' http://localhost:8080/api/v1/validations
```

It always answers 200 with a Validation Report: `valid`, the detected Message Version, the encoding, the transaction count, and every Validation Problem with its line, element, XPath, a `code`, the parser's raw `cause` and a plain-language `message` with an example of a valid value. The checks run in layers, and each layer runs only if the one before it passed:

1. well-formed XML, parsed with lxml hardened for untrusted input;
2. no DTD;
3. a supported Message Version namespace;
4. at most 500,000 elements;
5. valid against that version's XSD within a 10-second budget, in a pool of worker processes.

Files are capped at 10 MB, and the report lists at most 100 problems. Rules beyond the XSD (MDR or CBPR+ usage rules, IBAN checksums, `NbOfTxs` and `CtrlSum`) are not checked. In the Workbench, you drop or paste a file and get summary tiles, the source with problem lines highlighted, and a problem rail beside it. See [spec section 17](docs/spec.md#17-upload-validation).

### Validate from the command line

The same check runs on a laptop without Docker or a server, on macOS or Windows, with only [uv](https://docs.astral.sh/uv/) installed (uv fetches Python 3.13 itself). From the repo root of a checkout:

```sh
uv run --project backend pain validate batch.xml
uv run --project backend pain validate batch.xml --output-file report.md
```

Or install it once to put `pain` on the PATH, and run it from anywhere:

```sh
uv tool install ./backend
pain validate batch.xml --output-file report.md
```

On Windows, in PowerShell:

```powershell
uv tool install .\backend
pain validate C:\payments\pain.001.001.03.xml --output-file .\report.md
```

After pulling a newer version, run `uv tool install --reinstall ./backend` to update the installed `pain`. Inside the project environment, `python -m pain_demo validate ...` works too.

- **Output:** a summary (verdict, Message Version, transactions, problem count, encoding, file name, size, sha256), then each Validation Problem under its numbered source line with its `code` and plain-language `message`.
- **`--output-file PATH`** writes the report as Markdown instead: a summary table, then each problem with its line and two lines either side in an `xml` code block. An existing file is overwritten, and the folder must already exist. The terminal shows only a one-line summary and where the report went.
- **Exit codes:** 0 when the file is valid, 1 when it has problems, and 2 when it could not check the file (missing, empty or over 10 MB, or an unwritable output path).
- **Same limits and checks** as `POST /validations`, so a file gets the same report here, over the API and in the Workbench.

See [spec section 18](docs/spec.md#18-validation-cli).

### Sample File generation

- **Message Versions:** all eleven that pain001 supports, pain.001.001.03 to .13. The default is .03.
- **Up to 100 transactions per file.** Countries, currencies and amount ranges are set per request ([5](docs/spec.md#5-generation-request-model-and-supplied-data-merging)).
- **Supplied Data:** a nested JSON request, or a flat CSV (`POST /sample-files/csv`). Generated Data fills any gaps ([5.3](docs/spec.md#53-merging-field-by-field), [5.6](docs/spec.md#56-csv-format)).
- **Hits:** a Hit Count of drawn Hits (0 gives a clean file), plus Named Hits that say which Entity, Placement, Name Variant and transaction. Allowlists constrain the drawn Hits ([6](docs/spec.md#6-placement-selection-and-overrides)).
- **Placements:** Debtor, Creditor, Ultimate Debtor, Ultimate Creditor, Debtor Agent, Creditor Agent, Intermediary Agents 1 to 3, and remittance-information mentions. Every Placement works in every Message Version.
- **Name Variants:** exact, alias, native script, transliteration and fuzzed ([7](docs/spec.md#7-name-variants)).
- **Exposures:** clean transactions whose creditor side sits in RU, BY, IR, KP, SY or VE, to test country-based screening. They are listed separately from Hits ([8](docs/spec.md#8-exposures)).
- **Seeds:** the same request and Seed give a byte-identical Sample File and Answer Key within one Generator Version. Every file starts with an XML comment carrying its Seed and the app version ([9](docs/spec.md#9-seed-randomness-and-generator-version)).
- **Answer Key:** canonical JSON with the Effective Request, the Generator Version, and every Hit and Exposure with its XPath. A CSV projection comes from `POST /answer-keys/csv`, and `?format=zip` bundles the XML with both Answer Key files ([11](docs/spec.md#11-answer-key)).
- **Always valid:** every Sample File is XSD-validated before it is returned. A failure is a `500 build_failed` error, never a silently invalid file ([10.4](docs/spec.md#104-xsd-validation-and-the-build-report)).

The Entity Catalogue holds 50 real Sanctioned Entities (20 Banks, 16 Corporates and 14 Individuals) as one TOML file each in [`backend/src/pain_demo/catalogue/entities/`](backend/src/pain_demo/catalogue/entities/) ([3](docs/spec.md#3-entity-catalogue)).

## API

Everything is under `/api/v1`. The OpenAPI document is committed at [`backend/openapi.json`](backend/openapi.json), and interactive docs are served at `/docs`. The full contract is [spec section 12](docs/spec.md#12-api-contract).

| Endpoint | Purpose |
|---|---|
| `POST /validations` | Validate an Uploaded Message |
| `POST /sample-files` | Generate from a JSON request (`?format=zip` for a zip) |
| `POST /sample-files/csv` | Generate from a request part plus a Supplied Data CSV |
| `POST /answer-keys/csv` | Answer Key JSON in, its CSV out |
| `GET /entities`, `GET /entities/{id}` | The Entity Catalogue |
| `GET /options`, `GET /message-versions` | What a generation request may ask for, and its defaults |
| `GET /version` | The Generator Version |
| `GET /health` | Healthcheck |

## Decisions worth knowing

The reasoning behind each of these is in the linked ADR or spec section.

- **Our own API, not pain001's.** `/api/v1` is the only public contract, and pain001 is an internal dependency ([ADR-0001](docs/adr/0001-own-api-over-bundled-pain001-api.md)).
- **`pain001.corpus.build`, not the flat templates.** Only `corpus.build` can emit Intermediary Agents and every party in every Message Version. One renderer module holds every pain001 import ([ADR-0002](docs/adr/0002-corpus-build-over-flat-templates.md), [10](docs/spec.md#10-rendering-engine-and-version-fitting)).
- **Stateless and local.** There is no database, no auth and no job queue, and files are limited to 100 transactions. The app is for internal or local use only, published on `localhost:8080` ([1.2](docs/spec.md#12-settled-constraints)).
- **Pinned generator libraries.** `pain001`, `Faker`, `schwifty`, `iuliia` and `rapidfuzz` are pinned exactly, kept out of Dependabot, and recorded in the Generator Version. Upgrade them only with `just upgrade-generators` ([2.4](docs/spec.md#24-dependency-policy), [15.4](docs/spec.md#154-upgrade-procedures)).
- **Goldens guard the output.** Two fixed requests in all eleven Message Versions are byte-compared in CI. Any commit that changes a golden bumps the app's minor version, so a different version and different output for the same Seed mean the same thing ([9.5](docs/spec.md#95-goldens-and-upgrades), [15.3](docs/spec.md#153-goldens)).
- **No unplanned Hits.** Generated banks come only from a curated Clean Bank List, never from schwifty's registry, which names real sanctioned banks. Generated party names are screened against the catalogue and redrawn on a match ([4](docs/spec.md#4-clean-bank-list-and-unplanned-hit-screening)).
- **Upload Validation reuses pain001's XSDs**, so what we validate cannot drift from what we generate. An invalid upload is a 200 with a report, not an error ([17.2](docs/spec.md#172-response-always-200-with-a-validation-report), [17.4](docs/spec.md#174-schemas)).

## Developing

You need [uv](https://docs.astral.sh/uv/), [just](https://just.systems/), Node 24 with [pnpm](https://pnpm.io/) (`corepack enable` picks up the version pinned in `frontend/package.json`), and Docker for the compose stack.

- `just setup` installs backend and frontend dependencies and the prek hooks.
- `just dev` runs the API natively on http://127.0.0.1:8000, with docs at `/docs`. `just web-dev` runs the Workbench on Vite, with `/api` proxied to it.
- `just up` builds both images and starts the compose stack on http://localhost:8080, with the git SHA passed in. `just down` stops it.
- `just check` and `just test` are what CI runs, plus a Windows job that runs the CLI and Upload Validation tests. `just e2e` runs the Playwright smoke test against the compose stack.
- `just openapi` regenerates `backend/openapi.json` after an API change, and `just gen-client` regenerates the TypeScript client from it. CI fails on drift in either.
- `just goldens` regenerates the golden Sample Files. Bump the minor version in `backend/pyproject.toml` whenever a golden changes.
- `just upgrade-generators <library>[==<version>] ...` bumps a pinned generator library, regenerates the goldens and prints the diff.
- `just build-clean-banks` rebuilds the IBAN-country section of the Clean Bank List from schwifty's registry. Review the diff before committing.
- `just verify-catalogue` and `just verify-clean-banks` download the live OFAC SDN and UK Sanctions List files and report catalogue drift or Clean Bank List matches. These are manual checks and never run in CI.

Configuration is through `PAIN_DEMO_`-prefixed environment variables ([16](docs/spec.md#16-configuration)).

## Docs

- [`docs/spec.md`](docs/spec.md): build-ready spec, assembled from the wayfinder map
- [`CONTEXT.md`](CONTEXT.md): domain glossary
- [`docs/adr/`](docs/adr/): architecture decision records
- [`docs/agents/`](docs/agents/): how coding agents work with the issue tracker and domain docs
- [`NOTICE`](NOTICE): OGL v3.0 attribution and OFAC source citation

## Licence

Licensed under either of Apache License, Version 2.0 ([`LICENSE-APACHE`](LICENSE-APACHE)) or MIT license ([`LICENSE-MIT`](LICENSE-MIT)) at your option. The Entity Catalogue's list data stays under its source terms; see [`NOTICE`](NOTICE). Generated Sample Files and Answer Keys are yours to use; the source terms for catalogue names still apply.

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in the work by you, as defined in the Apache-2.0 license, shall be dual licensed as above, without any additional terms or conditions.
