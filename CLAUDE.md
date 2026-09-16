# CLAUDE.md

Sample ISO 20022 pain.001 generator for testing a sanctions Screening Tool. See `README.md` for what it is and `CONTEXT.md` for the domain language. Use the glossary terms (Sample File, Message Version, Entity Catalogue, Placement, Name Variant, Answer Key, Seed, ...) in code, issues and conversation.

## Current phase: planning

There is no application code yet. The design is tracked as a wayfinder map on GitHub Issues (the issue labelled `wayfinder:map` in `Tryline-Studios/pain-demo`), with decision tickets as sub-issues. The destination is a build-ready spec, not an implementation. Don't start building unless asked.

## Settled constraints

- Backend: Python 3.13, FastAPI, Astral tooling (uv, ruff, ty). Frontend: Vite, React, TypeScript, pnpm, TanStack Query, shadcn/ui, Biome, and a TS client generated from the OpenAPI spec. Deployed with docker-compose.
- No database, no auth, no job queue; internal/local use only; at most 100 transactions per Sample File.
- Our own `/api/v1` is the only public contract; pain001's bundled API is not used (ADR-0001).

## pain001 library gotchas

- Pin an exact version. It is pre-1.0 and ships several releases a day.
- Use `pain001.xml.generate_xml.generate_xml_string(rows, message_type, template_path, xsd_path)` for in-memory XML. `process_files` writes to disk.
- Its path validator rejects files outside the cwd, temp dir and package dir, so its file-based loaders can raise `SecurityError`. Pass rows as `list[dict]` instead.
- It registers XML namespaces process-wide. Generation is blocking, so run it off the event loop.

## Agent skills

### Issue tracker

GitHub Issues on `Tryline-Studios/pain-demo` via `gh`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: root `CONTEXT.md` + `docs/adr/`. See `docs/agents/domain.md`.
