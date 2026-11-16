"""The Validation CLI: `pain validate <file> [--output-file PATH]` (spec section 18)."""

import argparse
import html
import io
import os
import re
import sys
from pathlib import Path

from pain_demo import validation
from pain_demo.validation import ValidationProblem, ValidationReport


class _Refused(Exception):
    """Exit 2 with this one line on stderr."""


def _read(path: Path) -> bytes:
    try:
        if path.stat().st_size > validation.MAX_UPLOAD_BYTES:
            raise _Refused(f"{path} is over {validation.MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
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
    return text.splitlines()


def _line(problem: ValidationProblem, lines: list[str]) -> int | None:
    """The problem's line, if it has one in the file (a parser may place an error just past the end)."""
    return problem.line if problem.line and problem.line <= len(lines) else None


def _problem_count(report: ValidationReport) -> str:
    count = f"{len(report.problems)}{'+' if report.truncated else ''}"
    return f"{count} problem{'' if count == '1' else 's'}"


def _verdict(report: ValidationReport, paint: bool) -> str:
    verdict, colour = ("Valid", "32") if report.valid else ("Invalid", "31")
    verdict = f"\033[1;{colour}m{verdict}\033[0m" if paint else verdict
    return f"{verdict}  {report.message_version or 'unknown Message Version'}  {_problem_count(report)}"


def _terminal(report: ValidationReport, lines: list[str], paint: bool) -> str:
    def dim(text: str) -> str:
        return f"\033[2m{text}\033[0m" if paint else text

    def code(text: str) -> str:
        return f"\033[1;31m{text}\033[0m" if paint else text

    transactions = "unknown" if report.transaction_count is None else report.transaction_count
    out = [
        _verdict(report, paint),
        f"Transactions: {transactions}  Encoding: {report.encoding or 'unknown'}",
        f"{report.file.name}  {report.file.size_bytes:,} bytes  sha256 {report.file.sha256[:12]}",
        "",
    ]
    if report.valid:
        return "\n".join([*out, "No problems found"])
    width = len(str(len(lines)))
    for problem in report.problems:
        if not (line := _line(problem, lines)):
            continue
        source = lines[line - 1]
        out.append(f"{dim(f'{line:>{width}} |')} {source}")
        # XSD problems carry no column, so point at their element's tag on the line instead
        column = problem.column or (source.find(f"<{problem.tag}") + 1 if problem.tag else 0)
        if column > 0:
            out.append(f"{' ' * width}   {' ' * (column - 1)}^")
        out.extend([f"{code(problem.code)}: {problem.message}", ""])
    for problem in report.problems:
        if not _line(problem, lines):
            out.extend([f"{code(problem.code)}: {problem.message}", ""])
    return "\n".join(out).rstrip("\n")


def _validate(args: argparse.Namespace) -> int:
    output: Path | None = args.output_file
    if output is not None and not output.parent.is_dir():
        raise _Refused(f"the output folder {output.parent} does not exist")
    content = _read(args.file)
    try:
        report = validation.validate_message(content, args.file.name)
    except validation.WorkerUnavailable:
        raise _Refused(
            f"the schema check's worker did not start within {validation.XSD_START_SECONDS:g} seconds; try again"
        ) from None
    paint = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    lines = _lines(content, report)
    if output is None:
        print(_terminal(report, lines, paint))
    else:
        try:
            output.write_text(_markdown(report, lines), encoding="utf-8", newline="\n")
        except OSError as error:
            raise _Refused(f"cannot write {output}: {error.strerror}") from None
        print(f"{_verdict(report, paint)}\nReport written to {output}")
    return 0 if report.valid else 1


def _markdown(report: ValidationReport, lines: list[str]) -> str:
    rows = [
        ("Result", "Valid" if report.valid else "Invalid"),
        ("Message Version", report.message_version or "unknown"),
        ("Transactions", "unknown" if report.transaction_count is None else report.transaction_count),
        ("Problems", f"{len(report.problems)}{'+' if report.truncated else ''}"),
        ("Encoding", report.encoding or "unknown"),
        ("Size", f"{report.file.size_bytes:,} bytes"),
        ("sha256", report.file.sha256),
    ]
    out = [f"# {report.file.name}", "", "| | |", "|---|---|", *(f"| {k} | {v} |" for k, v in rows), ""]
    if report.valid:
        return "\n".join([*out, "No problems found", ""])
    out.extend(["## Problems", ""])
    # Windows of 2 lines either side; windows that overlap or touch merge into one block.
    blocks: list[tuple[int, int, list[ValidationProblem]]] = []
    located = [(line, p) for p in report.problems if (line := _line(p, lines))]
    for line, problem in sorted(located, key=lambda located: located[0]):
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
    unlocated = [p for p in report.problems if not _line(p, lines)]
    if unlocated:
        out.extend(["### Not tied to a line", "", *(_markdown_problem(p) for p in unlocated), ""])
    return "\n".join(out)


def _markdown_problem(problem: ValidationProblem) -> str:
    where = "" if problem.line is None else f" at {problem.line}" + (f":{problem.column}" if problem.column else "")
    item = [f"- **{problem.code}**{where}: {html.escape(problem.message, quote=False)}"]
    if problem.path:
        item.append(f"  `{problem.path}`")
    if problem.cause:
        item.append(f"  <details><summary>cause</summary>{html.escape(problem.cause, quote=False)}</details>")
    return "\n".join(item)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pain", description="Check pain.001 files.")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate a pain.001 file and print its Validation Report")
    validate.add_argument("file", type=Path, help="the pain.001 file, at most 10 MB")
    validate.add_argument("--output-file", type=Path, metavar="PATH", help="write the report here as Markdown")
    args = parser.parse_args(argv)  # a usage error exits 2 here
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # a legacy Windows code page never raises
    try:
        return _validate(args)
    except _Refused as refused:
        print(f"pain: {refused}", file=sys.stderr)
        return 2
    finally:
        validation.shutdown()
