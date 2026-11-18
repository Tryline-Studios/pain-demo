"""The Validation CLI: `pain validate <file> [--output-file PATH]` (spec section 18)."""

import argparse
import html
import io
import os
import re
import sys
from pathlib import Path
from typing import NoReturn

from pain_workbench import validation
from pain_workbench.validation import ValidationProblem, ValidationReport

_MAX_MB = validation.MAX_UPLOAD_BYTES // (1024 * 1024)


class _Refused(Exception):
    """Exit 2 with this one line on stderr."""


def _read(path: Path) -> bytes:
    try:
        if path.stat().st_size > validation.MAX_UPLOAD_BYTES:
            raise _Refused(f"{path} is over {_MAX_MB} MB")
        content = path.read_bytes()
    except OSError as error:
        raise _Refused(f"cannot read {path}: {error.strerror}") from None
    if not content:
        raise _Refused(f"{path} is empty")
    return content


def _lines(content: bytes, report: ValidationReport) -> list[str]:
    """The file's source lines, decoded as the report says (UTF-8 when it says nothing), bad bytes replaced."""
    try:
        text = content.decode(report.encoding or "utf-8", errors="replace")
    except LookupError:  # an encoding name Python does not know
        text = content.decode("utf-8", errors="replace")
    # Only the line breaks lxml counts; str.splitlines also splits on U+2028, U+0085 and others.
    return re.split(r"\r\n|\r|\n", text.removesuffix("\n").removesuffix("\r"))


def _located_line(problem: ValidationProblem, lines: list[str]) -> int | None:
    """The problem's line, if it has one in the file (a parser may place an error just past the end)."""
    return problem.line if problem.line and problem.line <= len(lines) else None


class _Summary:
    """What both reports show, worked out once."""

    def __init__(self, report: ValidationReport, lines: list[str]) -> None:
        self.problems = f"{len(report.problems)}{'+' if report.truncated else ''}"
        self.transactions = "unknown" if report.transaction_count is None else str(report.transaction_count)
        # The XSD does not report problems in line order (a parent's missing child comes after its children's
        # problems), so sort by line: the order a reader meets them in the file.
        located = [(line, p) for p in report.problems if (line := _located_line(p, lines))]
        self.located = sorted(located, key=lambda pair: pair[0])
        self.unlocated = [p for p in report.problems if not _located_line(p, lines)]

    def problem_count(self) -> str:
        return f"{self.problems} problem{'' if self.problems == '1' else 's'}"


def _paint(text: str, sgr: str, on: bool) -> str:
    return f"\033[{sgr}m{text}\033[0m" if on else text


def _verdict(report: ValidationReport, paint: bool) -> str:
    verdict, colour = ("Valid", "32") if report.valid else ("Invalid", "31")
    return _paint(verdict, f"1;{colour}", paint) + f"  {report.message_version or 'unknown Message Version'}"


def _tag_column(source: str, tag: str) -> int:
    """The 1-based column of `<tag` on the line, skipping longer tags that start the same (`<BIC` in `<BICFI`)."""
    match = re.search(rf"<{re.escape(tag)}(?=[\s>/]|$)", source)
    return match.start() + 1 if match else 0


def _terminal(report: ValidationReport, lines: list[str], summary: _Summary, paint: bool) -> str:
    def headline(code: str) -> str:
        return _paint(code, "1;31", paint)

    out = [
        f"{_verdict(report, paint)}  Transactions: {summary.transactions}  {summary.problem_count()}"
        f"  Encoding: {report.encoding or 'unknown'}",
        f"{report.file.name}  {report.file.size_bytes:,} bytes  sha256 {report.file.sha256[:12]}",
        "",
    ]
    if report.valid:
        return "\n".join([*out, "No problems found"])
    width = len(str(len(lines)))
    for line, problem in summary.located:
        source = lines[line - 1]
        out.append(f"{_paint(f'{line:>{width}} |', '2', paint)} {source}")
        # XSD problems carry no column, so point at their element's tag on the line instead
        column = problem.column or (_tag_column(source, problem.tag) if problem.tag else 0)
        if column > 0:
            out.append(f"{' ' * width}   {' ' * (column - 1)}^")
        out.extend([f"{headline(problem.code)}: {problem.message}", ""])
    for problem in summary.unlocated:
        out.extend([f"{headline(problem.code)}: {problem.message}", ""])
    return "\n".join(out).rstrip("\n")


def _validate(file: Path, output: Path | None) -> int:
    if output is not None and not output.parent.is_dir():
        raise _Refused(f"the output folder {output.parent} does not exist")
    content = _read(file)
    try:
        report = validation.validate_message(content, file.name)
    except validation.WorkerUnavailable:
        raise _Refused(
            f"the schema check's worker did not start within {validation.XSD_START_SECONDS:g} seconds; try again"
        ) from None
    paint = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    lines = _lines(content, report)
    summary = _Summary(report, lines)
    if output is None:
        print(_terminal(report, lines, summary, paint))
    else:
        try:
            output.write_text(_markdown(report, lines, summary), encoding="utf-8", newline="\n")
        except OSError as error:
            raise _Refused(f"cannot write {output}: {error.strerror}") from None
        print(f"{_verdict(report, paint)}  {summary.problem_count()}\nReport written to {output}")
    return 0 if report.valid else 1


def _markdown(report: ValidationReport, lines: list[str], summary: _Summary) -> str:
    rows = [
        ("Result", "Valid" if report.valid else "Invalid"),
        ("Message Version", report.message_version or "unknown"),
        ("Transactions", summary.transactions),
        ("Problems", summary.problems),
        ("Encoding", report.encoding or "unknown"),
        ("Size", f"{report.file.size_bytes:,} bytes"),
        ("sha256", report.file.sha256),
    ]
    table = (f"| {k} | {v.replace('|', '\\|')} |" for k, v in rows)
    out = [f"# {report.file.name}", "", "| | |", "|---|---|", *table, ""]
    if report.valid:
        return "\n".join([*out, "No problems found", ""])
    out.extend(["## Problems", ""])
    # Windows of 2 lines either side; windows that overlap or touch merge into one block.
    blocks: list[tuple[int, int, list[ValidationProblem]]] = []
    for line, problem in summary.located:
        start, end = max(1, line - 2), min(len(lines), line + 2)
        if blocks and start <= blocks[-1][1] + 1:
            first, last, problems = blocks[-1]
            blocks[-1] = (first, max(last, end), [*problems, problem])
        else:
            blocks.append((start, end, [problem]))
    for start, end, problems in blocks:
        out.extend([f"### Line {start}" if start == end else f"### Lines {start} to {end}", ""])
        out.extend(_markdown_problem(p) for p in problems)
        width = len(str(end))
        window = [f"  {n:>{width}} | {lines[n - 1]}" for n in range(start, end + 1)]
        fence = "`" * max([3, *(len(run) + 1 for run in re.findall("`+", "\n".join(window)))])
        out.extend(["", f"{fence}xml", *window, fence, ""])
    if summary.unlocated:
        out.extend(["### Not tied to a line", "", *(_markdown_problem(p) for p in summary.unlocated), ""])
    return "\n".join(out)


def _markdown_problem(problem: ValidationProblem) -> str:
    where = "" if problem.line is None else f" at {problem.line}" + (f":{problem.column}" if problem.column else "")
    item = [f"- **{problem.code}**{where}: {html.escape(problem.message, quote=False)}"]
    if problem.path:
        item.append(f"  `{problem.path}`")
    if problem.cause:
        item.append(f"  <details><summary>cause</summary>{html.escape(problem.cause, quote=False)}</details>")
    return "\n".join(item)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        """A usage error is one line on stderr and exit 2 (spec 18.3), not argparse's usage block."""
        self.exit(2, f"pain: {message}\n")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="pain", description="Check pain.001 files.")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate a pain.001 file and print its Validation Report")
    validate.add_argument("file", type=Path, help=f"the pain.001 file, at most {_MAX_MB} MB")
    validate.add_argument("--output-file", type=Path, metavar="PATH", help="write the report here as Markdown")
    args = parser.parse_args(argv)  # a usage error exits 2 here
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # a legacy Windows code page never raises
    try:
        return _validate(args.file, args.output_file)
    except _Refused as refused:
        print(f"pain: {refused}", file=sys.stderr)
        return 2
    finally:
        validation.shutdown()
