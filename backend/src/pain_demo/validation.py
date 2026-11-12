"""Upload Validation: check an Uploaded Message layer by layer and build its Validation Report (spec section 17)."""

import asyncio
import functools
import hashlib
import itertools
import multiprocessing
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from enum import StrEnum
from multiprocessing.connection import Connection

from lxml import etree
from pydantic import BaseModel, ConfigDict

from pain_demo import renderer
from pain_demo.generation.request import MESSAGE_VERSIONS

_NAMESPACE_PREFIX = "urn:iso:std:iso:20022:tech:xsd:"
_PARSER_POSITION = re.compile(r", line \d+, column \d+$")
MAX_PROBLEMS = 100
MAX_ELEMENTS = 500_000
"""Above the richest realistic 10 MB pain.001 (about 400,000 elements) and well below a flood (about 1.3 million)."""
XSD_BUDGET_SECONDS = 10
"""The longest the XSD layer may run before its worker process is stopped."""
XSD_START_SECONDS = 5
"""The longest a new worker process may take to start (about a quarter of a second normally) before it is stopped."""
XSD_WORKERS = 4
"""Upload Validations running at once; later ones queue for a worker."""
_ELEMENT = re.compile(r"^Element '(?:\{[^}]*\})?([^']+)'(?:, attribute '([^']+)')?: ")
_EXPECTED = re.compile(r"Expected is (?:one of )?\( (.*) \)")
_PATTERN = re.compile(r"The value '(.*)' is not accepted by the pattern '(.*)'")
_ENUMERATION = re.compile(r"The value '(.*)' is not an element of the set \{(.*)\}")
_DATATYPE = re.compile(r": '(.*)' is not a valid value of the atomic type '(?:\{[^}]*\})?([^']+)'")
_LENGTH = re.compile(r"length of '(\d+)'; this \w+ the allowed \w+ length of '(\d+)'")
_DIGITS = re.compile(r"The value '(.*)' has more (fractional )?digits than are allowed \('(\d+)'\)")
_XS = "{http://www.w3.org/2001/XMLSchema}"
_HINTS = [
    (re.compile(r"ISODate"), "a valid date", "YYYY-MM-DD, like 2009-12-31"),
    (re.compile(r"ISODateTime"), "a valid date and time", "YYYY-MM-DDThh:mm:ss, like 2009-12-31T09:30:00"),
    (re.compile(r"ISOYear"), "a valid year", "YYYY, like 2009"),
    (
        re.compile(r"PhoneNumber"),
        "an international phone number",
        "+, a country code, a hyphen and the number, like +1-123-456-7890",
    ),
    (
        re.compile(r"(Any)?BIC(FI)?(Dec2014)?Identifier"),
        "a valid BIC",
        "8 or 11 capital letters and digits, like DEUTDEFF or DEUTDEFF500",
    ),
    (
        re.compile(r"IBAN2007Identifier"),
        "a valid IBAN",
        "a two-letter country code, two check digits and up to 30 letters or digits with no spaces, "
        "like DE89370400440532013000",
    ),
    (re.compile(r"CountryCode"), "a country code", "two capital letters, like GB"),
    (re.compile(r"Active(OrHistoric)?CurrencyCode"), "a currency code", "three capital letters, like EUR"),
    (
        re.compile(r"Active(OrHistoric)?CurrencyAndAmount_SimpleType"),
        "a valid amount",
        "a number with a dot for decimals, like 1234.50",
    ),
    (
        re.compile(r"LEIIdentifier"),
        "a valid LEI",
        "20 capital letters or digits ending in two check digits, like 5493001KJTIIGC8Y1R12",
    ),
]
"""XSD type families (names vary by Message Version), what a value of one is, and what a valid one looks like."""


def _hint(type_name: str | None) -> tuple[str, str] | None:
    return next(((what, like) for family, what, like in _HINTS if type_name and family.fullmatch(type_name)), None)


@functools.cache
def _schema_types(version: str) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """Each complex type's child element and `@attribute` types ("" for the global elements), and each pattern's type.

    ISO 20022 XSDs declare every type at the top level, so one flat pass covers them.
    """
    xsd = renderer.xsd(version)
    children = {"": {el.attrib["name"]: el.attrib["type"] for el in xsd.iterfind(f"{_XS}element")}}
    for complex_type in xsd.iterfind(f"{_XS}complexType"):
        children[complex_type.attrib["name"]] = {
            ("@" if el.tag == f"{_XS}attribute" else "") + el.attrib["name"]: el.attrib["type"]
            for el in complex_type.iter(f"{_XS}element", f"{_XS}attribute")
        }
    patterns = {
        pattern.attrib["value"]: simple_type.attrib["name"]
        for simple_type in xsd.iterfind(f"{_XS}simpleType")
        for pattern in simple_type.iter(f"{_XS}pattern")
    }
    return children, patterns


def _type_of(version: str, element: etree._Element | None, attribute: str | None) -> str | None:
    """The XSD type of an element (or its attribute), followed down from Document; None where the walk breaks."""
    if element is None:
        return None
    names = [etree.QName(el).localname for el in [*reversed(list(element.iterancestors())), element]]
    children, _ = _schema_types(version)
    type_name = ""
    for name in [*names, f"@{attribute}"] if attribute else names:
        if (type_name := children.get(type_name, {}).get(name)) is None:
            return None
    return type_name


class ProblemCode(StrEnum):
    MALFORMED_XML = "malformed_xml"
    DTD_NOT_ALLOWED = "dtd_not_allowed"
    UNSUPPORTED_MESSAGE = "unsupported_message"
    TOO_MANY_ELEMENTS = "too_many_elements"
    VALIDATION_TIMED_OUT = "validation_timed_out"
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


def _layers_before_xsd(content: bytes) -> tuple[str, str, etree._Element]:
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


@functools.cache
def _schema(version: str) -> etree.XMLSchema:
    """A Message Version's XSD, compiled once per worker process and reused for its later uploads.

    Each worker runs one validation at a time: an XMLSchema's error log belongs to the schema, not the call, so it
    must never be shared between threads.
    """
    return etree.XMLSchema(renderer.xsd(version))


def _xsd_errors(root: etree._Element, version: str) -> list[etree._LogEntry]:
    schema = _schema(version)
    schema.validate(root)
    # lxml offers no error cap, so a hostile file runs until the worker's time budget stops it.
    return list(itertools.islice(schema.error_log, MAX_PROBLEMS + 1))


def _element(find: etree.XPathDocumentEvaluator, lxml_path: str | None) -> etree._Element | None:
    try:
        (element,) = find(lxml_path) if lxml_path else (None,)
    except (etree.XPathError, ValueError):
        return None
    return element


def _path(element: etree._Element | None) -> str | None:
    """lxml's path uses `*` for default-namespace steps; rebuild it from local names with 1-based positions."""
    if element is None:
        return None
    steps = []
    for el in [*reversed(list(element.iterancestors())), element]:
        name = etree.QName(el).localname
        same_name = f"{{*}}{name}"  # any namespace: positions count local names
        twins = sum(1 for _ in el.itersiblings(same_name, preceding=True))
        later = next(el.itersiblings(same_name), None) is not None
        steps.append(f"{name}[{twins + 1}]" if twins or later else name)
    return "/" + "/".join(steps)


def _classify(
    tag: str, attribute: str | None, line: int, error: etree._LogEntry, version: str, element: etree._Element | None
) -> tuple[ProblemCode, str]:
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
        if hint := _hint(_type_of(version, element, attribute) or _schema_types(version)[1].get(pattern)):
            what, like = hint
            message = f"{subject} '{value}' {where} is not {what}: expected {like} (pattern {pattern})"
            return ProblemCode.PATTERN_MISMATCH, message
        return ProblemCode.PATTERN_MISMATCH, f"{subject} '{value}' {where} doesn't match the pattern {pattern}"
    if error.type_name == "SCHEMAV_CVC_ENUMERATION_VALID" and (match := _ENUMERATION.search(cause)):
        value, allowed = match.groups()
        return ProblemCode.INVALID_VALUE, f"{subject} '{value}' {where} is not one of {allowed.replace("'", '')}"
    if error.type_name == "SCHEMAV_CVC_DATATYPE_VALID_1_2_1" and (match := _DATATYPE.search(cause)):
        value, datatype = match.groups()
        hint = _hint(datatype)
        expected = f": expected {hint[1]}" if hint else ""
        return ProblemCode.INVALID_VALUE, f"{subject} '{value}' {where} is not a valid {datatype}{expected}"
    if error.type_name == "SCHEMAV_CVC_MAXLENGTH_VALID" and (match := _LENGTH.search(cause)):
        length, limit = match.groups()
        return ProblemCode.TOO_LONG, f"{subject} {where} is {length} characters long; the maximum is {limit}"
    if error.type_name == "SCHEMAV_CVC_MINLENGTH_VALID" and (match := _LENGTH.search(cause)):
        length, limit = match.groups()
        return ProblemCode.TOO_SHORT, f"{subject} {where} is {length} characters long; the minimum is {limit}"
    if error.type_name in {"SCHEMAV_CVC_FRACTIONDIGITS_VALID", "SCHEMAV_CVC_TOTALDIGITS_VALID"} and (
        match := _DIGITS.search(cause)
    ):
        value, fractional, limit = match.groups()
        digits = "decimals" if fractional else "digits"
        message = f"{subject} '{value}' {where} has too many {digits}: expected at most {limit} {digits}, like 1234.50"
        return ProblemCode.INVALID_VALUE, message
    return ProblemCode.SCHEMA_VIOLATION, cause


def _schema_problem(find: etree.XPathDocumentEvaluator, version: str, error: etree._LogEntry) -> ValidationProblem:
    named = _ELEMENT.match(error.message)
    tag, attribute = named.groups() if named else (None, None)
    element = _element(find, error.path)
    if tag is None:
        code, message = ProblemCode.SCHEMA_VIOLATION, error.message
    else:
        code, message = _classify(tag, attribute, error.line, error, version, element)
    return ValidationProblem(
        line=error.line or None,
        column=error.column or None,  # libxml2 reports no column for schema errors (0); null rather than a fake one
        tag=tag,
        path=_path(element),
        code=code,
        cause=error.message,
        message=message,
    )


def _xsd_layer(content: bytes, version: str) -> tuple[list[ValidationProblem], int]:
    """The XSD layer's problems and the transaction count, for content that passed the earlier layers."""
    root = etree.fromstring(content, _parser())
    tree = root.getroottree()
    # lxml's error paths use the document's own prefixes, so the XPath needs them all.
    namespaces = {prefix: uri for el in tree.iter() for prefix, uri in el.nsmap.items() if prefix}
    find = etree.XPathDocumentEvaluator(tree, namespaces=namespaces)
    problems = [_schema_problem(find, version, error) for error in _xsd_errors(root, version)]
    return problems, len(root.findall(f".//{{{etree.QName(root).namespace}}}CdtTrfTxInf"))


def _serve(conn: Connection) -> None:
    """A worker process: answers XSD layer requests until its parent goes away."""
    conn.send(None)  # ready: imports done
    while True:
        try:
            content, version = conn.recv()
        except EOFError:
            return
        conn.send(_xsd_layer(content, version))


_SPAWN = multiprocessing.get_context("spawn")  # fork is unsafe in a threaded server


class _Worker:
    """One worker process, reused between uploads so it compiles each Message Version's schema once."""

    def __init__(self) -> None:
        self.conn, child = _SPAWN.Pipe()
        self.process = _SPAWN.Process(target=_serve, args=(child,), daemon=True, name="xsd-worker")
        self.process.start()
        child.close()
        self.ready = False

    def run(self, content: bytes, version: str) -> tuple[list[ValidationProblem], int] | None:
        """The XSD layer's result, or None past the budget; `WorkerUnavailable` if the process never starts."""
        if not self.ready:
            # Start-up is not the upload's budget, but it has its own.
            if not self.conn.poll(XSD_START_SECONDS):
                raise WorkerUnavailable
            self.ready = self.conn.recv() is None
        self.conn.send((content, version))
        return self.conn.recv() if self.conn.poll(XSD_BUDGET_SECONDS) else None

    def stop(self) -> None:
        self.process.kill()  # libxml2 cannot be interrupted any other way
        self.process.join()
        self.conn.close()


class WorkerUnavailable(Exception):
    """A worker process did not start within `XSD_START_SECONDS`; it has been stopped."""


_threads: list[ThreadPoolExecutor] = []
"""The Upload Validation threads, started on first use: never the pool generation uses, so a slow validation holds
none of its threads. A list so `shutdown` can empty it and the next app start a fresh one."""
_idle: list[_Worker] = []
_lock = threading.Lock()


def _run_xsd_layer(content: bytes, version: str) -> tuple[list[ValidationProblem], int] | None:
    with _lock:
        worker = _idle.pop() if _idle else None
    worker = worker or _Worker()
    try:
        result = worker.run(content, version)
    except BaseException:
        worker.stop()
        raise
    if result is None:
        worker.stop()
        worker = _Worker()
    with _lock:
        _idle.append(worker)  # last in, first out: a replacement serves the next upload
    return result


async def validate(content: bytes, name: str | None) -> ValidationReport:
    """`validate_message` on the Upload Validation threads."""
    with _lock:
        if not _threads:
            _threads.append(ThreadPoolExecutor(XSD_WORKERS, thread_name_prefix="upload-validation"))
        future = _threads[0].submit(validate_message, content, name)
    return await asyncio.wrap_future(future)


def shutdown() -> None:
    """Wait for the running validations (each ends within its budgets), then stop the threads and idle workers."""
    with _lock:
        threads = _threads.copy()
        _threads.clear()
    for executor in threads:
        executor.shutdown(wait=True)
    with _lock:
        idle = _idle.copy()
        _idle.clear()
    for worker in idle:
        worker.stop()


def validate_message(content: bytes, name: str | None) -> ValidationReport:
    """Blocking: the XSD layer runs in a worker process within `XSD_BUDGET_SECONDS`."""
    try:
        encoding, version, root = _layers_before_xsd(content)
    except _Rejected as rejected:
        encoding, version, problems, transaction_count = rejected.encoding, rejected.version, [rejected.problem], None
    else:
        del root  # the worker parses its own copy; free this one while it runs
        if (result := _run_xsd_layer(content, version)) is None:
            message = f"The schema check took longer than its {XSD_BUDGET_SECONDS:g}-second budget and was stopped"
            problems = [ValidationProblem(code=ProblemCode.VALIDATION_TIMED_OUT, message=message)]
            transaction_count = None
        else:
            problems, transaction_count = result
    return ValidationReport(
        valid=not problems,
        message_version=version,
        encoding=encoding,
        transaction_count=transaction_count,
        file=UploadedFile(name=name, size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest()),
        problems=problems[:MAX_PROBLEMS],
        truncated=len(problems) > MAX_PROBLEMS,
    )
