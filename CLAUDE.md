# CLAUDE.md

Sample ISO 20022 pain.001 generator for testing a sanctions Screening Tool. See `README.md` for what it is and `CONTEXT.md` for the domain language. Use the glossary terms (Sample File, Message Version, Entity Catalogue, Placement, Name Variant, Answer Key, Seed, ...) in code, issues and conversation.

## Current phase: planning

There is no application code yet. The design is tracked as a wayfinder map on GitHub Issues (the issue labelled `wayfinder:map` in `Tryline-Studios/pain-demo`), with decision tickets as sub-issues. The destination is a build-ready spec, not an implementation. Don't start building unless asked.

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
