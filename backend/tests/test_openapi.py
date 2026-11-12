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
        "too_many_elements",
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


def test_generate_sample_file_answers_json_or_a_zip() -> None:
    operation = create_app().openapi()["paths"]["/api/v1/sample-files"]["post"]

    (format_parameter,) = operation["parameters"]
    assert (format_parameter["name"], format_parameter["in"]) == ("format", "query")
    assert format_parameter["schema"]["enum"] == ["json", "zip"]
    content = operation["responses"]["200"]["content"]
    assert content["application/json"]["schema"] == {"$ref": "#/components/schemas/GeneratedSampleFile"}
    assert content["application/zip"]["schema"] == {"type": "string", "format": "binary"}


def test_the_transaction_cap_and_seed_length_are_published() -> None:
    properties = create_app().openapi()["components"]["schemas"]["GenerationRequest"]["properties"]

    (count,) = [s for s in properties["transaction_count"]["anyOf"] if s["type"] == "integer"]
    assert (count["minimum"], count["maximum"]) == (1, 100)
    (seed,) = [s for s in properties["seed"]["anyOf"] if s["type"] == "string"]
    assert seed["maxLength"] == 64


def test_every_operation_declares_only_the_problem_responses_it_can_return() -> None:
    document = create_app().openapi()

    declared = {
        (path, method): {status for status in operation["responses"] if status >= "400"}
        for path, methods in document["paths"].items()
        for method, operation in methods.items()
    }
    assert declared == {
        ("/api/v1/sample-files", "post"): {"413", "422", "500"},
        ("/api/v1/message-versions", "get"): {"500"},
        ("/api/v1/options", "get"): {"500"},
        ("/api/v1/health", "get"): {"500"},
        ("/api/v1/version", "get"): {"500"},
        ("/api/v1/entities", "get"): {"422", "500"},
        ("/api/v1/entities/{entity_id}", "get"): {"404", "422", "500"},
        ("/api/v1/validations", "post"): {"413", "415", "422", "500"},
    }
    paths = document["paths"]
    assert "build_failed" in paths["/api/v1/sample-files"]["post"]["responses"]["500"]["description"]
    assert "build_failed" not in paths["/api/v1/options"]["get"]["responses"]["500"]["description"]


def test_every_problem_response_is_problem_json() -> None:
    document = create_app().openapi()

    def ref(name: str) -> dict:
        return {"application/problem+json": {"schema": {"$ref": f"#/components/schemas/{name}"}}}

    for path, methods in document["paths"].items():
        for method, operation in methods.items():
            for status, response in operation["responses"].items():
                if status == "422":
                    assert response["content"] == ref("RequestValidationProblem"), (path, method)
                elif status >= "400":
                    assert response["content"] == ref("Problem"), (path, method, status)

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
