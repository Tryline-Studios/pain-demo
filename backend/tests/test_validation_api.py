"""Upload Validation through the HTTP seam (spec section 17)."""

import hashlib
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

URL = "/api/v1/validations"
XML = {"Content-Type": "application/xml"}


def pain001(version: str = "03") -> bytes:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.{version}">\n'
        f"  <CstmrCdtTrfInitn/>\n"
        f"</Document>\n"
    ).encode()


def test_a_raw_xml_body_of_a_supported_version_reports_valid(client: TestClient) -> None:
    content = pain001("03")

    response = client.post(URL, content=content, headers=XML)

    assert response.status_code == 200
    assert response.json() == {
        "valid": True,
        "message_version": "pain.001.001.03",
        "encoding": "UTF-8",
        "transaction_count": None,
        "file": {"name": None, "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()},
        "problems": [],
        "truncated": False,
    }


def problems_of(client: TestClient, content: bytes) -> list[dict[str, Any]]:
    response = client.post(URL, content=content, headers=XML)
    assert response.status_code == 200
    report = response.json()
    assert report["valid"] is (report["problems"] == [])
    return report["problems"]


@pytest.mark.parametrize("version", [f"{n:02d}" for n in range(3, 14)])
def test_every_supported_message_version_is_detected(client: TestClient, version: str) -> None:
    report = client.post(URL, content=pain001(version), headers=XML).json()

    assert (report["valid"], report["message_version"]) == (True, f"pain.001.001.{version}")


def test_a_multipart_file_reports_its_name(client: TestClient) -> None:
    content = pain001("09")

    response = client.post(URL, files={"file": ("batch.xml", content, "application/xml")})

    assert response.status_code == 200
    assert response.json()["file"] == {
        "name": "batch.xml",
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    assert response.json()["message_version"] == "pain.001.001.09"


@pytest.mark.parametrize("content_type", ["application/json", "text/plain", "text/xml"])
def test_any_other_content_type_is_a_415_problem(client: TestClient, content_type: str) -> None:
    response = client.post(URL, content=pain001(), headers={"Content-Type": content_type})

    assert response.status_code == 415
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Unsupported Media Type"


def test_a_missing_content_type_is_a_415_problem(client: TestClient) -> None:
    assert client.post(URL, content=pain001()).status_code == 415


@pytest.mark.parametrize(
    "send",
    [
        pytest.param({"content": b"", "headers": XML}, id="empty raw body"),
        pytest.param({"files": {"file": ("empty.xml", b"", "application/xml")}}, id="empty file part"),
        pytest.param({"files": {"other": ("batch.xml", b"<a/>", "application/xml")}}, id="no file part"),
        pytest.param({"data": {"file": "<a/>"}, "files": {"x": ("x", b"x")}}, id="file as a text field"),
    ],
)
def test_a_missing_or_empty_file_is_a_422_validation_error(client: TestClient, send: dict[str, Any]) -> None:
    response = client.post(URL, **send)

    assert response.status_code == 422
    assert response.json()["type"] == "validation_error"
    assert response.json()["errors"][0]["field"] == "file"


def test_malformed_xml_is_one_problem_with_its_position(client: TestClient) -> None:
    content = b'<?xml version="1.0"?>\n<Document>\n  <CstmrCdtTrfInitn>\n</Document>\n'

    report = client.post(URL, content=content, headers=XML).json()

    assert (report["valid"], report["message_version"], report["encoding"]) == (False, None, None)
    (problem,) = report["problems"]
    assert problem["code"] == "malformed_xml"
    assert (problem["line"], problem["path"], problem["tag"]) == (4, None, None)
    assert isinstance(problem["column"], int)
    assert "Opening and ending tag mismatch" in problem["cause"]
    assert problem["message"].startswith("The file is not well-formed XML: Opening and ending tag mismatch")
    assert problem["message"].endswith(f"(line 4, column {problem['column']})")


def test_undecodable_bytes_are_malformed_xml(client: TestClient) -> None:
    content = pain001().replace(b"<CstmrCdtTrfInitn/>", b"<CstmrCdtTrfInitn>\xff</CstmrCdtTrfInitn>")

    (problem,) = problems_of(client, content)

    assert (problem["code"], problem["line"]) == ("malformed_xml", 3)


def test_an_encoding_lxml_does_not_know_is_malformed_xml(client: TestClient) -> None:
    (problem,) = problems_of(client, pain001().replace(b"UTF-8", b"no-such-encoding"))

    assert problem["code"] == "malformed_xml"


@pytest.mark.parametrize(
    ("content", "encoding"),
    [
        pytest.param(pain001().split(b"\n", 1)[1], "UTF-8", id="no declaration"),
        pytest.param(b"\xef\xbb\xbf" + pain001().split(b"\n", 1)[1], "UTF-8", id="BOM, no declaration"),
        pytest.param(
            pain001().replace(b"UTF-8", b"ISO-8859-1").replace(b"<CstmrCdtTrfInitn/>", b"<Nm>Soci\xe9t\xe9</Nm>"),
            "ISO-8859-1",
            id="ISO-8859-1",
        ),
        pytest.param(pain001().decode().replace("UTF-8", "UTF-16").encode("utf-16"), "UTF-16", id="UTF-16"),
    ],
)
def test_the_declared_or_default_encoding_is_accepted_and_reported(
    client: TestClient, content: bytes, encoding: str
) -> None:
    report = client.post(URL, content=content, headers=XML).json()

    assert (report["valid"], report["encoding"]) == (True, encoding)


def test_a_doctype_is_not_allowed(client: TestClient) -> None:
    content = pain001().replace(b"<Document", b"<!DOCTYPE Document>\n<Document", 1)

    (problem,) = problems_of(client, content)

    assert problem["code"] == "dtd_not_allowed"


def test_an_external_entity_is_never_resolved(client: TestClient, tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET")
    content = (
        f'<?xml version="1.0"?>\n<!DOCTYPE Document [<!ENTITY xxe SYSTEM "{secret.as_uri()}">]>\n'
        f'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"><Nm>&xxe;</Nm></Document>\n'
    ).encode()

    response = client.post(URL, content=content, headers=XML)

    assert "TOP-SECRET" not in response.text
    assert [p["code"] for p in response.json()["problems"]] == ["dtd_not_allowed"]


def test_an_entity_expansion_bomb_is_harmless(client: TestClient) -> None:
    entities = '<!ENTITY lol0 "lol">' + "".join(f'<!ENTITY lol{i} "{f"&lol{i - 1};" * 10}">' for i in range(1, 10))
    content = (
        f'<?xml version="1.0"?>\n<!DOCTYPE Document [{entities}]>\n'
        f'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"><Nm>&lol9;</Nm></Document>\n'
    ).encode()

    started = time.perf_counter()
    response = client.post(URL, content=content, headers=XML)

    assert time.perf_counter() - started < 2
    assert len(response.content) < 2000
    # libxml2's amplification guard may reject the DTD as malformed before our own DOCTYPE check sees it.
    (problem,) = response.json()["problems"]
    assert problem["code"] in {"dtd_not_allowed", "malformed_xml"}


@pytest.mark.parametrize(
    ("root", "found"),
    [
        ('<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.02">', "pain.001.001.02"),
        ('<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.14">', "pain.001.001.14"),
        ('<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">', "pacs.008.001.08"),
        ('<Document xmlns="urn:example:pain.001.001.03">', "urn:example:pain.001.001.03"),
        ("<Document>", "no namespace"),
    ],
)
def test_an_unsupported_root_namespace_is_named(client: TestClient, root: str, found: str) -> None:
    content = f'<?xml version="1.0"?>\n{root}<CstmrCdtTrfInitn/></Document>\n'.encode()

    report = client.post(URL, content=content, headers=XML).json()

    assert report["message_version"] is None
    (problem,) = report["problems"]
    assert (problem["code"], problem["line"], problem["tag"], problem["path"]) == (
        "unsupported_message",
        2,
        "Document",
        "/Document",
    )
    assert found in problem["message"]


def test_a_root_other_than_document_is_unsupported(client: TestClient) -> None:
    content = pain001().replace(b"Document", b"AppHdr")

    (problem,) = problems_of(client, content)

    assert (problem["code"], problem["tag"]) == ("unsupported_message", "AppHdr")


TEN_MEGABYTES = 10 * 1024 * 1024


def padded(size: int) -> bytes:
    """A supported pain.001 message padded with trailing comments to exactly `size` bytes (in small nodes, since
    libxml2 without huge-tree mode rejects a single 10 MB text run)."""
    content = pain001()
    comments, spaces = divmod(size - len(content), len(b"<!---->\n"))
    return content + b"<!---->\n" * comments + b" " * spaces


def test_a_body_of_ten_megabytes_is_accepted(client: TestClient) -> None:
    response = client.post(URL, content=padded(TEN_MEGABYTES), headers=XML)

    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_a_body_over_ten_megabytes_is_a_413_problem(client: TestClient) -> None:
    response = client.post(URL, content=padded(TEN_MEGABYTES + 1), headers=XML)

    assert response.status_code == 413
    assert response.json()["detail"] == "Request body exceeds 10 MB"


def test_a_chunked_multipart_body_over_ten_megabytes_is_a_413_problem(client: TestClient) -> None:
    def chunks() -> Iterator[bytes]:
        yield b"--b\r\nContent-Disposition: form-data; name=file; filename=big.xml\r\n\r\n"
        for _ in range(11):
            yield b" " * (1024 * 1024)
        yield b"\r\n--b--\r\n"

    response = client.post(URL, content=chunks(), headers={"Content-Type": "multipart/form-data; boundary=b"})

    assert response.status_code == 413
    assert response.json()["detail"] == "Request body exceeds 10 MB"


def test_other_routes_keep_the_one_megabyte_cap(client: TestClient) -> None:
    response = client.post("/api/v1/health", content=b" " * (1024 * 1024 + 1), headers=XML)

    assert response.json()["detail"] == "Request body exceeds 1 MB"
