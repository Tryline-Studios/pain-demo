"""The committed OpenAPI document (spec section 12.5)."""

import json

from pain_demo.app import create_app
from pain_demo.openapi import OPENAPI_PATH, render_openapi
from pain_demo.version import app_version


def test_meta_operations_are_named_and_tagged() -> None:
    paths = create_app().openapi()["paths"]

    assert paths["/api/v1/health"]["get"]["operationId"] == "get_health"
    assert paths["/api/v1/health"]["get"]["tags"] == ["meta"]
    assert paths["/api/v1/version"]["get"]["operationId"] == "get_version"
    assert paths["/api/v1/version"]["get"]["tags"] == ["meta"]


def test_validate_message_takes_multipart_or_xml_and_returns_a_validation_report() -> None:
    document = create_app().openapi()
    operation = document["paths"]["/api/v1/validations"]["post"]

    assert (operation["operationId"], operation["tags"]) == ("validate_message", ["validation"])
    assert set(operation["requestBody"]["content"]) == {"multipart/form-data", "application/xml"}
    schemas = document["components"]["schemas"]
    assert set(schemas["ValidationReport"]["required"]) == {
        "valid",
        "message_version",
        "encoding",
        "transaction_count",
        "file",
        "problems",
        "truncated",
    }
    assert schemas["ProblemCode"]["enum"] == [
        "malformed_xml",
        "dtd_not_allowed",
        "unsupported_message",
        "missing_element",
        "unexpected_element",
        "pattern_mismatch",
        "invalid_value",
        "too_long",
        "too_short",
        "schema_violation",
    ]


def test_sample_file_operations_are_named_and_tagged() -> None:
    paths = create_app().openapi()["paths"]

    for path, method, operation_id in [
        ("/api/v1/sample-files", "post", "generate_sample_file"),
        ("/api/v1/message-versions", "get", "list_message_versions"),
        ("/api/v1/options", "get", "get_options"),
    ]:
        assert (paths[path][method]["operationId"], paths[path][method]["tags"]) == (operation_id, ["sample-files"])


def test_the_transaction_cap_and_seed_length_are_published() -> None:
    properties = create_app().openapi()["components"]["schemas"]["GenerationRequest"]["properties"]

    (count,) = [s for s in properties["transaction_count"]["anyOf"] if s["type"] == "integer"]
    assert (count["minimum"], count["maximum"]) == (1, 100)
    (seed,) = [s for s in properties["seed"]["anyOf"] if s["type"] == "string"]
    assert seed["maxLength"] == 64


def test_every_operation_describes_its_problem_responses() -> None:
    document = create_app().openapi()

    def ref(name: str) -> dict:
        return {"application/problem+json": {"schema": {"$ref": f"#/components/schemas/{name}"}}}

    for path, methods in document["paths"].items():
        for method, operation in methods.items():
            responses = operation["responses"]
            assert responses["422"]["content"] == ref("RequestValidationProblem"), (path, method)
            assert responses["500"]["content"] == ref("Problem"), (path, method)
            if method == "post":
                assert responses["413"]["content"] == ref("Problem"), (path, method)
            for status, response in responses.items():
                if status >= "400":
                    assert list(response["content"]) == ["application/problem+json"], (path, method, status)

    schemas = document["components"]["schemas"]
    assert "HTTPValidationError" not in schemas
    assert "ValidationError" not in schemas
    assert schemas["RequestValidationProblem"]["properties"]["errors"]["items"] == {
        "$ref": "#/components/schemas/FieldError"
    }
    assert "line" in schemas["ValidationProblem"]["properties"], "the Upload Validation problem keeps its name"


def test_info_version_is_the_app_semver() -> None:
    assert create_app().openapi()["info"]["version"] == app_version()


def test_the_committed_document_is_current() -> None:
    assert json.loads(OPENAPI_PATH.read_text(encoding="utf-8")) == json.loads(render_openapi()), "run `just openapi`"


def test_the_rendered_document_ends_with_a_newline() -> None:
    assert render_openapi().endswith("}\n")
