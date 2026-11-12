# CLAUDE.md

Sample ISO 20022 pain.001 generator for testing a sanctions Screening Tool. See `README.md` for what it is and `CONTEXT.md` for the domain language. Use the glossary terms (Sample File, Message Version, Entity Catalogue, Placement, Name Variant, Answer Key, Seed, Generator Version, ...) in code, issues and conversation.

## Current phase: build

The build-ready spec is `docs/spec.md`; it is the source of truth for behaviour, and every section names the ticket it came from. Work is cut into GitHub issues labelled `ready-for-agent` on `Tryline-Studios/pain-demo`, each linking the spec sections it implements and listing its acceptance criteria and blockers. Pick a ticket, implement it on a branch, keep `just check` and `just test` green, open a PR. The design map (the issue labelled `wayfinder:map`) is history now; do not reopen settled decisions there.

## Working in the backend

- `backend/` is a uv src-layout project, package `pain_demo`, Python 3.13 pinned. Run everything through the root `justfile`: `just setup` (deps and prek hooks), `just check` (ruff, ty, Biome, tsc, OpenAPI and client drift), `just test` (pytest and Vitest), `just dev` (native API with reload), `just openapi` (regenerate `backend/openapi.json`; run it after any route or model change or CI fails on drift).
- Tests are pytest under `backend/tests`, in-process through FastAPI's test client. Warnings are errors. Test at public seams (HTTP, `Settings`, log output), not internals.
- The `app.py` factory wires the skeleton: `Settings` (`PAIN_DEMO_` prefix, `settings.py`), structlog (`log_config.py`), the request id and one-event-per-request middleware (`request_context.py`), the 1 MB body cap (`body_limit.py`) and RFC 9457 problem details (`problems.py`). New endpoints go in `api/v1/<tag>.py` routers with snake_case `operation_id`s and one of the tags `sample-files`, `catalogue`, `meta`, `validation`.
- Raise `HTTPException` or let request validation fail; the problem handlers shape every error. Never write an error body by hand. The one other error path is the renderer's `RenderFailed`, which `problems.py` shapes as a 500 `build_failed`.
- The Entity Catalogue is the `catalogue/` package: one TOML file per Entity in `catalogue/entities/<id>.toml` and `catalogue/control_relationships.toml`, the Pydantic schema in `catalogue/schema.py` (every model forbids unknown fields), `load_catalogue` in `catalogue/loader.py` collecting every problem before raising `CatalogueError`, and `catalogue/capabilities.py` for the Name Variants and Placements an Entity supports. `create_app` loads it once, logs `catalogue_invalid` at CRITICAL and exits 1 on failure, and keeps it on `app.state.catalogue`; the Generator Version's `catalogue_snapshot` is the latest Listing verification date. Tests build scratch catalogues in `tmp_path` and pass `catalogue_root=` to `create_app` or `load_catalogue`. Catalogue values come from the roster write-up on the `research/entity-catalogue-roster` branch.
- The Clean Bank List is `generation/clean_banks.toml` (spec section 4), loaded by `generation/clean_banks.py` after the catalogue: `create_app` logs `clean_bank_list_invalid` at CRITICAL and exits 1 if it is malformed or shares a BIC8 or normalised name with the catalogue, and keeps it on `app.state.clean_banks`. `just build-clean-banks` rewrites its IBAN-country section from schwifty's registry; the US section is hand-maintained. Tests pass `clean_banks_path=` to `create_app` or `load_clean_banks`. BIC validation and TOML problem collection shared with the catalogue live in `identifiers.py` and `validated_files.py`.
- The Generator Version block lives in `version.py`; the five generator libraries (`pain001`, `Faker`, `schwifty`, `iuliia`, `rapidfuzz`) are pinned exactly and excluded from Dependabot. Bump them only with `just upgrade-generators <library>[==<version>] ...` (spec section 15.4), which rewrites the pins, regenerates the goldens and prints the diff.
- Goldens are `backend/tests/goldens/{clean,kitchen-sink}/`: two fixed requests in all eleven Message Versions, byte-compared by `tests/test_goldens.py`, which also asserts the kitchen sink still covers every Placement and Name Variant. Regenerate with `just goldens`. Any commit that changes a golden, including a catalogue, Clean Bank List or generator pin change, bumps the app's minor version in `backend/pyproject.toml` (then `uv lock` and `just goldens` again, since Answer Keys record it). PRs are squash-merged, so each merged PR that changes a golden bumps the minor version once (spec 9.5).

## Working in the frontend

- `frontend/` is Vite, React, TypeScript and pnpm (pinned via `packageManager`, Node 24 in `.node-version`). Pure TypeScript: no `.js`, `.jsx` or `.mjs`, and config files are `.ts`. Biome formats and lints; `just web-lint`, `just web-typecheck`, `just web-test` and `just gen-client-check` are what CI runs, `just web-dev` runs Vite with `/api` proxied to `just dev`.
- The UI talks to the API only through the generated client in `src/api/client.ts` (openapi-fetch and openapi-react-query over `src/api/schema.d.ts`). After any API change run `just openapi` then `just gen-client`, and commit both files; CI fails on drift. Never hand-edit `schema.d.ts` or call `fetch` directly.
- The Workbench (`src/workbench/`) is one screen with no router: a resizable settings pane (File, Data, Hits sections), a drag handle, and the output pane. shadcn/ui components live in `src/components/ui/` and are added with `pnpm dlx shadcn add <name>`; keep them as generated.
- Tests are Vitest with React Testing Library and MSW under `src/`, at the seam of a rendered component and the mocked API (`src/test/`). The Playwright smoke test in `e2e/` runs against the compose stack (`just up` then `just e2e`).
- The compose stack (`compose.yaml`, the two Dockerfiles, `frontend/Caddyfile`) publishes only `localhost:8080`; Caddy serves the build and proxies `/api`, so there is no CORS middleware anywhere. `just up` passes the git SHA into the API image.

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
