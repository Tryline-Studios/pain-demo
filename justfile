# Task runner for pain-demo. Backend recipes run in ./backend through uv; see docs/spec.md section 15.

set shell := ["bash", "-euo", "pipefail", "-c"]

# List recipes
default:
    @just --list

# Install backend dependencies and prek hooks
[working-directory: 'backend']
setup:
    uv sync --locked
    uv run prek install

# Format backend code
[working-directory: 'backend']
fmt:
    uv run ruff format .
    uv run ruff check --fix .

# ruff format and lint
[working-directory: 'backend']
lint:
    uv run ruff format --check .
    uv run ruff check .

# ty type check
[working-directory: 'backend']
typecheck:
    uv run ty check

# Everything CI checks except the tests: lint, typecheck and OpenAPI drift
check: lint typecheck openapi-check

# pytest
[working-directory: 'backend']
test *args:
    uv run pytest {{ args }}

# Run the API natively with reload
[working-directory: 'backend']
dev:
    uv run fastapi dev src/pain_demo/main.py

# Regenerate backend/openapi.json from the app, no server needed
[working-directory: 'backend']
openapi:
    uv run python -m pain_demo.openapi

# Fail if backend/openapi.json is out of date
[working-directory: 'backend']
openapi-check:
    uv run python -m pain_demo.openapi --check
