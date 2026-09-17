# CLAUDE.md

Sample ISO 20022 pain.001 generator for testing a sanctions Screening Tool. See `README.md` for what it is and `CONTEXT.md` for the domain language. Use the glossary terms (Sample File, Message Version, Entity Catalogue, Placement, Name Variant, Answer Key, Seed, Generator Version, ...) in code, issues and conversation.

## Current phase: build

The build-ready spec is `docs/spec.md`; it is the source of truth for behaviour, and every section names the ticket it came from. Work is cut into GitHub issues labelled `ready-for-agent` on `Tryline-Studios/pain-demo`, each linking the spec sections it implements and listing its acceptance criteria and blockers. Pick a ticket, implement it on a branch, keep `just check` and `just test` green, open a PR. The design map (the issue labelled `wayfinder:map`) is history now; do not reopen settled decisions there.

## Working in the backend

- `backend/` is a uv src-layout project, package `pain_demo`, Python 3.13 pinned. Run everything through the root `justfile`: `just setup` (deps and prek hooks), `just check` (ruff, ty, OpenAPI drift), `just test`, `just dev` (native API with reload), `just openapi` (regenerate `backend/openapi.json`; run it after any route or model change or CI fails on drift).
- Tests are pytest under `backend/tests`, in-process through FastAPI's test client. Warnings are errors. Test at public seams (HTTP, `Settings`, log output), not internals.
- The `app.py` factory wires the skeleton: `Settings` (`PAIN_DEMO_` prefix, `settings.py`), structlog (`logging.py`), the request id and one-event-per-request middleware (`request_context.py`), the 1 MB body cap (`body_limit.py`) and RFC 9457 problem details (`problems.py`). New endpoints go in `api/v1/<tag>.py` routers with snake_case `operation_id`s and one of the tags `sample-files`, `catalogue`, `meta`.
- Raise `HTTPException` or let request validation fail; the problem handlers shape every error. Never write an error body by hand.
- The Generator Version block lives in `version.py`; the five generator libraries (`pain001`, `Faker`, `schwifty`, `iuliia`, `rapidfuzz`) are pinned exactly and excluded from Dependabot. Bump them only via the upgrade procedure in spec section 15.4.

## Settled constraints

- Backend: Python 3.13, FastAPI, Astral tooling (uv, ruff, ty). Frontend: Vite, React, TypeScript, pnpm, TanStack Query, shadcn/ui, Biome, and a TS client generated from the OpenAPI spec. Deployed with docker-compose.
- No database, no auth, no job queue; internal/local use only; at most 100 transactions per Sample File.
- Our own `/api/v1` is the only public contract; pain001's bundled API is not used (ADR-0001).

## pain001 library gotchas

- Pin an exact version of `pain001[fast]` (the extra supplies lxml). It is pre-1.0 and ships several releases a day; goldens in CI catch output drift on upgrade.
- Build XML with `pain001.corpus.build(scenario, version)` (ADR-0002). It emits every party and agent role in every Message Version, renames `BIC`/`BICFI` per version, and XSD-validates the result. Do not use `generate_xml_string` or the bundled templates: they cannot emit Intermediary Agents and .04 to .08 are thin.
- Only the renderer module imports pain001. Map our own model to the scenario dict there; never expose pain001 types or its scenario schema elsewhere.
- Pass every identifier explicitly (no `auto` ids) and do not use `raw` merges. Read the build report: a dropped Placement is an error, any other drop is a warning.
- `corpus.build` checks the XSD only. Ultimate Debtor at one level and contiguous Intermediary Agents are enforced by our model; `pain001.corpus.rules.mdr.evaluate_mdr` is for tests.
- Its path validator rejects files outside the cwd, temp dir and package dir, so its file-based loaders can raise `SecurityError`. Keep everything in memory.
- It registers XML namespaces process-wide. Generation is blocking, so run it off the event loop.

## Agent skills

### Issue tracker

GitHub Issues on `Tryline-Studios/pain-demo` via `gh`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: root `CONTEXT.md` + `docs/adr/`. See `docs/agents/domain.md`.
