# pain-demo

Generates sample **ISO 20022 pain.001** (Customer Credit Transfer Initiation) files for testing and proving a sanctions payment screening tool.

Each Sample File mixes generated fake payment data (or data you supply) with real Sanctioned Entities from the OFAC SDN and UK Sanctions List, such as Sberbank and Evraz PLC, and comes with an Answer Key that says exactly what the screening tool should flag.

> **Status:** in build. The backend skeleton (health, version, tooling, CI) is in; generation is not. The build-ready spec is [`docs/spec.md`](docs/spec.md), the work is tracked as GitHub issues labelled `ready-for-agent`, and the decisions behind the spec live on the issue labelled `wayfinder:map` ([#1](https://github.com/Tryline-Studios/pain-demo/issues/1)).

## Planned shape

- **Backend:** Python 3.13, FastAPI, built on the [pain001](https://github.com/sebastienrousseau/pain001) library, with uv, ruff and ty
- **Frontend:** React, Vite, TypeScript
- **API first:** a versioned REST API at `/api/v1` that the web UI and scripts/CI both use
- **Deployment:** docker-compose, for internal or local use only with no authentication
- **Message versions:** every pain.001 version pain001 supports (pain.001.001.03 to .13), with .03 as the default

## Running the backend

Needs [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/). `just setup` installs dependencies and the prek hooks; `just dev` runs the API natively on http://127.0.0.1:8000 (`GET /api/v1/health`, `GET /api/v1/version`, docs at `/docs`); `just check` and `just test` are what CI runs.

## Docs

- [`docs/spec.md`](docs/spec.md): build-ready spec, assembled from the wayfinder map
- [`CONTEXT.md`](CONTEXT.md): domain glossary
- [`docs/adr/`](docs/adr/): architecture decision records
