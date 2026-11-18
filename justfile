# Task runner for pain-workbench. Backend recipes run in ./backend through uv, frontend recipes in ./frontend through
# pnpm; see docs/spec.md section 15.

set shell := ["bash", "-euo", "pipefail", "-c"]

# List recipes
default:
    @just --list

# Install backend and frontend dependencies and the prek hooks
setup: backend-setup web-setup

# Everything CI checks except the tests: lint, typecheck, OpenAPI and client drift
check: backend-lint backend-typecheck openapi-check web-lint web-typecheck gen-client-check

# All lint checks
lint: backend-lint web-lint

# All type checks
typecheck: backend-typecheck web-typecheck

# Backend and frontend unit tests
test: backend-test web-test

# Format everything
fmt: backend-fmt web-fmt

# --- backend ---

[working-directory: 'backend']
backend-setup:
    uv sync --locked
    uv run prek install

[working-directory: 'backend']
backend-fmt:
    uv run ruff format .
    uv run ruff check --fix .

# ruff format and lint
[working-directory: 'backend']
backend-lint:
    uv run ruff format --check .
    uv run ruff check .

# ty type check
[working-directory: 'backend']
backend-typecheck:
    uv run ty check

# pytest, with any extra arguments passed through
[working-directory: 'backend']
backend-test *args:
    uv run pytest {{ args }}

# Rewrite the committed goldens from the current Generator Version; review the diff and bump the minor version
[working-directory: 'backend']
goldens:
    UPDATE_GOLDENS=1 uv run pytest tests/test_goldens.py

# Bump generator pins (pain001, faker, schwifty, iuliia, rapidfuzz; `name==version` for a given one), regenerate the goldens and show the diff
[working-directory: 'backend']
upgrade-generators +libraries:
    uv run python -m pain_workbench.upgrade_generators {{ libraries }}

# Run the API natively with reload on http://127.0.0.1:8000
[working-directory: 'backend']
dev:
    uv run fastapi dev src/pain_workbench/main.py

# Regenerate backend/openapi.json from the app, no server needed
[working-directory: 'backend']
openapi:
    uv run python -m pain_workbench.openapi

# Fail if backend/openapi.json is out of date
[working-directory: 'backend']
openapi-check:
    uv run python -m pain_workbench.openapi --check

# Rewrite the IBAN-country section of the Clean Bank List from schwifty's registry minus catalogue matches; review the diff
[working-directory: 'backend']
build-clean-banks:
    uv run python -m pain_workbench.generation.build_clean_banks

# Download the live OFAC SDN and UK Sanctions List files and report catalogue drift; exits 1 on drift, 2 on a list it cannot parse
[working-directory: 'backend']
verify-catalogue:
    uv run python -m pain_workbench.freshness catalogue

# Download the live OFAC SDN and UK Sanctions List files and report Clean Bank List matches; exits 1 on a match, 2 on a list it cannot parse
[working-directory: 'backend']
verify-clean-banks:
    uv run python -m pain_workbench.freshness clean-banks

# --- frontend ---

[working-directory: 'frontend']
web-setup:
    pnpm install --frozen-lockfile

[working-directory: 'frontend']
web-fmt:
    pnpm exec biome check --write .

# Biome format and lint
[working-directory: 'frontend']
web-lint:
    pnpm exec biome ci .

# tsc
[working-directory: 'frontend']
web-typecheck:
    pnpm exec tsc --noEmit

# Vitest
[working-directory: 'frontend']
web-test *args:
    pnpm exec vitest run {{ args }}

# Run the Workbench natively with Vite proxying /api to `just dev`
[working-directory: 'frontend']
web-dev:
    pnpm dev

# Regenerate the TypeScript client types from backend/openapi.json
[working-directory: 'frontend']
gen-client:
    pnpm run gen-client

# Fail if the generated client is out of date
[working-directory: 'frontend']
gen-client-check:
    pnpm run gen-client
    git diff --exit-code -- src/api/schema.d.ts

# --- stack ---

# Build both images and start the compose stack on http://localhost:8080
up:
    GIT_SHA="$(git rev-parse HEAD)" docker compose up --build --detach --wait

# Stop the compose stack
down:
    docker compose down

# Playwright smoke test against the running compose stack; E2E_BASE_URL overrides http://localhost:8080
[working-directory: 'frontend']
e2e *args:
    pnpm exec playwright test {{ args }}
