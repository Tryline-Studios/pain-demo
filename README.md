# pain-demo

Generates sample **ISO 20022 pain.001** (Customer Credit Transfer Initiation) files for testing and proving a sanctions payment screening tool.

Each Sample File mixes generated fake payment data (or data you supply) with real Sanctioned Entities from OFAC and OFSI/FCDO lists, such as Sberbank and Evraz PLC, and comes with an Answer Key that says exactly what the screening tool should flag.

> **Status:** planning. The design is being worked out on the GitHub issue labelled `wayfinder:map`. There is no application code yet.

## Planned shape

- **Backend:** Python 3.13, FastAPI, built on the [pain001](https://github.com/sebastienrousseau/pain001) library, with uv, ruff and ty
- **Frontend:** React, Vite, TypeScript
- **API first:** a versioned REST API at `/api/v1` that the web UI and scripts/CI both use
- **Deployment:** docker-compose, for internal or local use only with no authentication
- **Message versions:** every pain.001 version pain001 supports (pain.001.001.03 to .13), with .03 as the default

## Docs

- [`CONTEXT.md`](CONTEXT.md): domain glossary
- [`docs/adr/`](docs/adr/): architecture decision records
