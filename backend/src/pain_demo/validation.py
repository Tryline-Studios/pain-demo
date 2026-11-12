"""Upload Validation: check an Uploaded Message layer by layer and build its Validation Report (spec section 17)."""

import hashlib
import re
import threading
from enum import StrEnum

from lxml import etree
from pydantic import BaseModel

from pain_demo import renderer

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


def _check(content: bytes) -> tuple[str | None, str | None, etree._Element | None, ValidationProblem | None]:
    """The first three layers; returns the encoding, the Message Version, the root once all pass, or the problem."""
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
    return encoding, version, root, None


MAX_PROBLEMS = 100
_SCHEMA_LOCKS = {version: threading.Lock() for version in MESSAGE_VERSIONS}
_ELEMENT = re.compile(r"^Element '(?:\{[^}]*\})?([^']+)'(?:, attribute '([^']+)')?: ")
_EXPECTED = re.compile(r"Expected is (?:one of )?\( (.*) \)")
_PATTERN = re.compile(r"The value '(.*)' is not accepted by the pattern '(.*)'")
_ENUMERATION = re.compile(r"The value '(.*)' is not an element of the set \{(.*)\}")
_DATATYPE = re.compile(r": '(.*)' is not a valid value of the atomic type '(?:\{[^}]*\})?([^']+)'")
_LENGTH = re.compile(r"length of '(\d+)'; this \w+ the allowed \w+ length of '(\d+)'")


def _xsd_errors(root: etree._Element, version: str) -> list[etree._LogEntry]:
    schema = renderer.schema(version)
    # One compiled schema is shared by every request thread, and its error log is per schema, not per call.
    with _SCHEMA_LOCKS[version]:
        schema.validate(root)
        return list(schema.error_log)


def _path(tree: etree._ElementTree, lxml_path: str) -> str | None:
    """lxml's path uses `*` for default-namespace steps; rebuild it from local names with 1-based positions."""
    namespaces = {prefix: uri for el in tree.iter() for prefix, uri in el.nsmap.items() if prefix}
    try:
        (element,) = tree.xpath(lxml_path, namespaces=namespaces)
    except (etree.XPathError, ValueError):
        return None
    steps = []
    for el in [*reversed(list(element.iterancestors())), element]:
        name = etree.QName(el).localname
        twins = [s for s in el.itersiblings(preceding=True) if etree.QName(s).localname == name]
        later = any(etree.QName(s).localname == name for s in el.itersiblings())
        steps.append(f"{name}[{len(twins) + 1}]" if twins or later else name)
    return "/" + "/".join(steps)


def _classify(tag: str, attribute: str | None, line: int, error: etree._LogEntry) -> tuple[ProblemCode, str]:
    cause = error.message
    subject = f"{tag} attribute {attribute}" if attribute else tag
    where = f"on line {line}"
    if error.type_name == "SCHEMAV_ELEMENT_CONTENT" and (expected := _EXPECTED.search(cause)):
        names = ", ".join(re.sub(r"\{[^}]*\}", "", name) for name in expected.group(1).split(", "))
        if "Missing child element" in cause:
            return ProblemCode.MISSING_ELEMENT, f"{tag} {where} is missing a child element; expected {names}"
        return ProblemCode.UNEXPECTED_ELEMENT, f"{tag} {where} is not expected here; expected {names}"
    if error.type_name == "SCHEMAV_ELEMENT_CONTENT" and cause.endswith("This element is not expected."):
        return ProblemCode.UNEXPECTED_ELEMENT, f"{tag} {where} is not expected here"
    if error.type_name == "SCHEMAV_CVC_PATTERN_VALID" and (match := _PATTERN.search(cause)):
        value, pattern = match.groups()
        return ProblemCode.PATTERN_MISMATCH, f"{subject} '{value}' {where} doesn't match the pattern {pattern}"
    if error.type_name == "SCHEMAV_CVC_ENUMERATION_VALID" and (match := _ENUMERATION.search(cause)):
        value, allowed = match.groups()
        return ProblemCode.INVALID_VALUE, f"{subject} '{value}' {where} is not one of {allowed.replace("'", '')}"
    if error.type_name == "SCHEMAV_CVC_DATATYPE_VALID_1_2_1" and (match := _DATATYPE.search(cause)):
        value, datatype = match.groups()
        return ProblemCode.INVALID_VALUE, f"{subject} '{value}' {where} is not a valid {datatype}"
    if error.type_name == "SCHEMAV_CVC_MAXLENGTH_VALID" and (match := _LENGTH.search(cause)):
        length, limit = match.groups()
        return ProblemCode.TOO_LONG, f"{subject} {where} is {length} characters long; the maximum is {limit}"
    if error.type_name == "SCHEMAV_CVC_MINLENGTH_VALID" and (match := _LENGTH.search(cause)):
        length, limit = match.groups()
        return ProblemCode.TOO_SHORT, f"{subject} {where} is {length} characters long; the minimum is {limit}"
    return ProblemCode.SCHEMA_VIOLATION, cause


def _schema_problem(tree: etree._ElementTree, error: etree._LogEntry) -> ValidationProblem:
    element = _ELEMENT.match(error.message)
    tag, attribute = element.groups() if element else (None, None)
    if tag is None:
        code, message = ProblemCode.SCHEMA_VIOLATION, error.message
    else:
        code, message = _classify(tag, attribute, error.line, error)
    return ValidationProblem(
        line=error.line or None,
        column=error.column or None,  # libxml2 reports no column for schema errors (0); null rather than a fake one
        tag=tag,
        path=_path(tree, error.path) if error.path else None,
        code=code,
        cause=error.message,
        message=message,
    )


def validate_message(content: bytes, name: str | None) -> ValidationReport:
    """Blocking: callers on the event loop run it in a thread."""
    encoding, version, root, problem = _check(content)
    problems = [problem] if problem else []
    transaction_count = None
    if root is not None and version is not None:
        tree = root.getroottree()
        errors = _xsd_errors(root, version)
        problems = [_schema_problem(tree, error) for error in errors[: MAX_PROBLEMS + 1]]
        transaction_count = len(root.findall(f".//{{{etree.QName(root).namespace}}}CdtTrfTxInf"))
    return ValidationReport(
        valid=not problems,
        message_version=version,
        encoding=encoding,
        transaction_count=transaction_count,
        file=UploadedFile(name=name, size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest()),
        problems=problems[:MAX_PROBLEMS],
        truncated=len(problems) > MAX_PROBLEMS,
    )
