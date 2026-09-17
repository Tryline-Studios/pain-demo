"""The committed OpenAPI document (spec section 12.5)."""

import json
from pathlib import Path

from pain_demo.app import create_app
from pain_demo.openapi import OPENAPI_PATH, render_openapi
from pain_demo.version import app_version


def test_meta_operations_are_named_and_tagged() -> None:
    paths = create_app().openapi()["paths"]

    assert paths["/api/v1/health"]["get"]["operationId"] == "get_health"
    assert paths["/api/v1/health"]["get"]["tags"] == ["meta"]
    assert paths["/api/v1/version"]["get"]["operationId"] == "get_version"
    assert paths["/api/v1/version"]["get"]["tags"] == ["meta"]


def test_info_version_is_the_app_semver() -> None:
    assert create_app().openapi()["info"]["version"] == app_version()


def test_the_committed_document_is_current() -> None:
    assert Path(__file__).resolve().parent.parent / "openapi.json" == OPENAPI_PATH
    assert json.loads(OPENAPI_PATH.read_text()) == json.loads(render_openapi()), "run `just openapi`"


def test_the_rendered_document_ends_with_a_newline() -> None:
    assert render_openapi().endswith("}\n")
