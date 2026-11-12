"""Upload Validation: check an Uploaded Message layer by layer and build its Validation Report (spec section 17)."""

import hashlib
import itertools
import re
from enum import StrEnum

from lxml import etree
from pydantic import BaseModel, ConfigDict

from pain_demo import renderer
from pain_demo.generation.request import MESSAGE_VERSIONS

_NAMESPACE_PREFIX = "urn:iso:std:iso:20022:tech:xsd:"
_PARSER_POSITION = re.compile(r", line \d+, column \d+$")
MAX_PROBLEMS = 100
MAX_ELEMENTS = 500_000
"""Above the richest realistic 10 MB pain.001 (about 400,000 elements) and well below a flood (about 1.3 million)."""
_ELEMENT = re.compile(r"^Element '(?:\{[^}]*\})?([^']+)'(?:, attribute '([^']+)')?: ")
_EXPECTED = re.compile(r"Expected is (?:one of )?\( (.*) \)")
_PATTERN = re.compile(r"The value '(.*)' is not accepted by the pattern '(.*)'")
_ENUMERATION = re.compile(r"The value '(.*)' is not an element of the set \{(.*)\}")
_DATATYPE = re.compile(r": '(.*)' is not a valid value of the atomic type '(?:\{[^}]*\})?([^']+)'")
_LENGTH = re.compile(r"length of '(\d+)'; this \w+ the allowed \w+ length of '(\d+)'")


class ProblemCode(StrEnum):
    MALFORMED_XML = "malformed_xml"
    DTD_NOT_ALLOWED = "dtd_not_allowed"
    UNSUPPORTED_MESSAGE = "unsupported_message"
    TOO_MANY_ELEMENTS = "too_many_elements"
    MISSING_ELEMENT = "missing_element"
    UNEXPECTED_ELEMENT = "unexpected_element"
    PATTERN_MISMATCH = "pattern_mismatch"
    INVALID_VALUE = "invalid_value"
    TOO_LONG = "too_long"
    TOO_SHORT = "too_short"
    SCHEMA_VIOLATION = "schema_violation"


class ValidationProblem(BaseModel):
    # The defaults are for building problems; every field is still always in the response.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    line: int | None = None
    column: int | None = None
    tag: str | None = None
    path: str | None = None
    code: ProblemCode
    cause: str | None = None
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


def _doctype_line(content: bytes, encoding: str) -> int | None:
    """lxml keeps no position for the DOCTYPE, so find it in the decoded text."""
    try:
        text = content.decode(encoding)
    except (LookupError, UnicodeDecodeError):
        return None
    offset = text.find("<!DOCTYPE")
    return text.count("\n", 0, offset) + 1 if offset >= 0 else None


class _Rejected(Exception):
    """An Uploaded Message stopped before the XSD layer, with its one problem."""

    def __init__(self, problem: ValidationProblem, encoding: str | None = None, version: str | None = None) -> None:
        self.problem = problem
        self.encoding = encoding
        self.version = version


def _parse_message(content: bytes) -> tuple[str, str, etree._Element]:
    """The first four layers: returns the encoding, the Message Version and the root, or raises `_Rejected`."""
    try:
        root = etree.fromstring(content, _parser())
    except etree.XMLSyntaxError as error:
        line, column = error.position
        clean = _PARSER_POSITION.sub("", error.msg).strip()
        message = f"The file is not well-formed XML: {clean} (line {line}, column {column})"
        problem = ValidationProblem(
            line=line, column=column, code=ProblemCode.MALFORMED_XML, cause=error.msg, message=message
        )
        raise _Rejected(problem) from None
    docinfo = root.getroottree().docinfo
    encoding = docinfo.encoding
    if docinfo.doctype:
        message = "The file declares a DOCTYPE; a pain.001 message must not carry a DTD"
        problem = ValidationProblem(
            line=_doctype_line(content, encoding), code=ProblemCode.DTD_NOT_ALLOWED, message=message
        )
        raise _Rejected(problem, encoding)
    qname = etree.QName(root)
    version = qname.namespace.removeprefix(_NAMESPACE_PREFIX) if qname.namespace else None
    if qname.localname != "Document" or version not in MESSAGE_VERSIONS:
        found = f"'{qname.namespace}'" if qname.namespace else "no namespace"
        message = (
            f"Root element '{qname.localname}' has {found}; expected a Document in "
            f"{_NAMESPACE_PREFIX}pain.001.001.03 to .13"
        )
        problem = ValidationProblem(
            line=root.sourceline,
            tag=qname.localname,
            path=f"/{qname.localname}",
            code=ProblemCode.UNSUPPORTED_MESSAGE,
            message=message,
        )
        raise _Rejected(problem, encoding)
    elements = sum(1 for _ in root.iter(etree.Element))
    if elements > MAX_ELEMENTS:
        message = f"The file has {elements:,} elements; the limit is {MAX_ELEMENTS:,}"
        raise _Rejected(ValidationProblem(code=ProblemCode.TOO_MANY_ELEMENTS, message=message), encoding, version)
    return encoding, version, root


def _xsd_errors(root: etree._Element, version: str) -> list[etree._LogEntry]:
    schema = renderer.schema(version)  # this thread's own, so concurrent uploads never wait for each other
    schema.validate(root)
    # shortcut: lxml offers no error cap and records every XSD error with a path that walks the preceding siblings,
    # so a hostile file under MAX_ELEMENTS can take minutes (about 4 at the cap), on its own worker thread only.
    # Bound the validation itself (a killable worker process or a time budget) if that bites.
    return list(itertools.islice(schema.error_log, MAX_PROBLEMS + 1))


def _path(find: etree.XPathDocumentEvaluator, lxml_path: str) -> str | None:
    """lxml's path uses `*` for default-namespace steps; rebuild it from local names with 1-based positions."""
    try:
        (element,) = find(lxml_path)
    except (etree.XPathError, ValueError):
        return None
    steps = []
    for el in [*reversed(list(element.iterancestors())), element]:
        name = etree.QName(el).localname
        same_name = f"{{*}}{name}"  # any namespace: positions count local names
        twins = sum(1 for _ in el.itersiblings(same_name, preceding=True))
        later = next(el.itersiblings(same_name), None) is not None
        steps.append(f"{name}[{twins + 1}]" if twins or later else name)
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


def _schema_problem(find: etree.XPathDocumentEvaluator, error: etree._LogEntry) -> ValidationProblem:
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
        path=_path(find, error.path) if error.path else None,
        code=code,
        cause=error.message,
        message=message,
    )


def validate_message(content: bytes, name: str | None) -> ValidationReport:
    """Blocking: callers on the event loop run it in a thread."""
    try:
        encoding, version, root = _parse_message(content)
    except _Rejected as rejected:
        encoding, version, problems, transaction_count = rejected.encoding, rejected.version, [rejected.problem], None
    else:
        tree = root.getroottree()
        # lxml's error paths use the document's own prefixes, so the XPath needs them all.
        namespaces = {prefix: uri for el in tree.iter() for prefix, uri in el.nsmap.items() if prefix}
        find = etree.XPathDocumentEvaluator(tree, namespaces=namespaces)
        errors = _xsd_errors(root, version)
        problems = [_schema_problem(find, error) for error in errors]
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
