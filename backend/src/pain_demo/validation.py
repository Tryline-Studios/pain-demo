"""Upload Validation: check an Uploaded Message layer by layer and build its Validation Report (spec section 17)."""

import hashlib
import re
from enum import StrEnum

from lxml import etree
from pydantic import BaseModel

MESSAGE_VERSIONS = tuple(f"pain.001.001.{n:02d}" for n in range(3, 14))
_NAMESPACE_PREFIX = "urn:iso:std:iso:20022:tech:xsd:"
_PARSER_POSITION = re.compile(r", line \d+, column \d+$")


class ProblemCode(StrEnum):
    MALFORMED_XML = "malformed_xml"
    DTD_NOT_ALLOWED = "dtd_not_allowed"
    UNSUPPORTED_MESSAGE = "unsupported_message"
    MISSING_ELEMENT = "missing_element"
    UNEXPECTED_ELEMENT = "unexpected_element"
    PATTERN_MISMATCH = "pattern_mismatch"
    INVALID_VALUE = "invalid_value"
    TOO_LONG = "too_long"
    TOO_SHORT = "too_short"
    SCHEMA_VIOLATION = "schema_violation"


class ValidationProblem(BaseModel):
    line: int | None
    column: int | None
    tag: str | None
    path: str | None
    code: ProblemCode
    cause: str | None
    message: str


class UploadedFile(BaseModel):
    name: str | None
    size_bytes: int
    sha256: str


class ValidationReport(BaseModel):
    valid: bool
    message_version: str | None
    encoding: str | None
    transaction_count: int | None
    file: UploadedFile
    problems: list[ValidationProblem]
    truncated: bool


def _parser() -> etree.XMLParser:
    """Hardened for untrusted input: no entity expansion, no network, no DTD loading, no huge-tree mode."""
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)


def _check(content: bytes) -> tuple[str | None, str | None, ValidationProblem | None]:
    """The first three layers; returns the encoding, the Message Version and the first problem found."""
    try:
        root = etree.fromstring(content, _parser())
    except etree.XMLSyntaxError as error:
        line, column = error.position
        cause = error.msg
        clean = _PARSER_POSITION.sub("", cause).strip()
        message = f"The file is not well-formed XML: {clean} (line {line}, column {column})"
        return (
            None,
            None,
            ValidationProblem(
                line=line,
                column=column,
                tag=None,
                path=None,
                code=ProblemCode.MALFORMED_XML,
                cause=cause,
                message=message,
            ),
        )
    docinfo = root.getroottree().docinfo
    encoding = docinfo.encoding
    if docinfo.doctype:
        message = "The file declares a DOCTYPE; a pain.001 message must not carry a DTD"
        return (
            encoding,
            None,
            ValidationProblem(
                line=None,
                column=None,
                tag=None,
                path=None,
                code=ProblemCode.DTD_NOT_ALLOWED,
                cause=None,
                message=message,
            ),
        )
    qname = etree.QName(root)
    version = qname.namespace.removeprefix(_NAMESPACE_PREFIX) if qname.namespace else None
    if qname.localname != "Document" or version not in MESSAGE_VERSIONS:
        found = f"'{qname.namespace}'" if qname.namespace else "no namespace"
        message = (
            f"Root element '{qname.localname}' has {found}; expected a Document in "
            f"{_NAMESPACE_PREFIX}pain.001.001.03 to .13"
        )
        return (
            encoding,
            None,
            ValidationProblem(
                line=root.sourceline,
                column=None,
                tag=qname.localname,
                path=f"/{qname.localname}",
                code=ProblemCode.UNSUPPORTED_MESSAGE,
                cause=None,
                message=message,
            ),
        )
    return encoding, version, None


def validate_message(content: bytes, name: str | None) -> ValidationReport:
    """Blocking: callers on the event loop run it in a thread."""
    encoding, version, problem = _check(content)
    problems = [problem] if problem else []
    return ValidationReport(
        valid=not problems,
        message_version=version,
        encoding=encoding,
        transaction_count=None,
        file=UploadedFile(name=name, size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest()),
        problems=problems,
        truncated=False,
    )
