"""Render the OpenAPI document offline: `python -m pain_workbench.openapi` writes `backend/openapi.json`."""

import json
import sys
from pathlib import Path

from pain_workbench.app import create_app
from pain_workbench.settings import Settings

OPENAPI_PATH = Path(__file__).resolve().parents[2] / "openapi.json"


def render_openapi() -> str:
    """The document as committed: 2-space indent, key order as FastAPI emits it, trailing newline."""
    app = create_app(Settings(log_format="json", log_level="WARNING", git_sha="openapi"))
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    if sys.argv[1:] == ["--check"]:
        if not OPENAPI_PATH.exists() or OPENAPI_PATH.read_text(encoding="utf-8") != render_openapi():
            print(f"{OPENAPI_PATH} is out of date: run `just openapi`", file=sys.stderr)
            return 1
        return 0
    OPENAPI_PATH.write_text(render_openapi(), encoding="utf-8")
    print(f"wrote {OPENAPI_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
