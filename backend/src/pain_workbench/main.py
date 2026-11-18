"""ASGI entry point: `fastapi dev src/pain_workbench/main.py` natively, `uvicorn pain_workbench.main:app` in Docker."""

from pain_workbench.app import create_app

app = create_app()
