"""ASGI entry point: `fastapi dev src/pain_demo/main.py` natively, `uvicorn pain_demo.main:app` in the container."""

from pain_demo.app import create_app

app = create_app()
