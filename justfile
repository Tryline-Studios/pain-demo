# Task runner for pain-demo. Backend recipes run in ./backend through uv; see docs/spec.md section 15.

set shell := ["bash", "-euo", "pipefail", "-c"]

backend := justfile_directory() / "backend"

# List recipes
default:
    @just --list

# Install backend dependencies and prek hooks
setup:
    cd "{{ backend }}" && uv sync --locked
    cd "{{ backend }}" && uv run prek install

# Format backend code
fmt:
    cd "{{ backend }}" && uv run ruff format .
    cd "{{ backend }}" && uv run ruff check --fix .

# ruff format and lint
lint:
    cd "{{ backend }}" && uv run ruff format --check .
    cd "{{ backend }}" && uv run ruff check .

# ty type check
typecheck:
    cd "{{ backend }}" && uv run ty check

# Everything CI checks except the tests: lint, typecheck and OpenAPI drift
check: lint typecheck openapi-check

# pytest
test *args:
    cd "{{ backend }}" && uv run pytest {{ args }}

# Run the API natively with reload
dev:
    cd "{{ backend }}" && uv run fastapi dev src/pain_demo/main.py

# Regenerate backend/openapi.json from the app, no server needed
openapi:
    cd "{{ backend }}" && uv run python -m pain_demo.openapi

# Fail if backend/openapi.json is out of date
openapi-check:
    cd "{{ backend }}" && uv run python -m pain_demo.openapi --check
