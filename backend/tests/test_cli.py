"""The Validation CLI through its public seam, `main([...])` (spec section 18)."""

import hashlib
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from test_validation_api import BAD_CURRENCY, pain001, with_transactions

from pain_demo.cli import main

GOLDEN = Path(__file__).parent / "goldens" / "clean" / "pain.001.001.03.xml"


def test_python_dash_m_pain_demo_validate_runs_the_cli() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pain_demo", "validate", str(GOLDEN)], capture_output=True, check=False, timeout=60
    )

    assert (result.returncode, result.stderr) == (0, b"")
    assert result.stdout.decode().replace("\r\n", "\n").endswith("\nNo problems found\n")


def test_a_valid_golden_exits_0_and_says_no_problems_found(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(GOLDEN)]) == 0

    out = capsys.readouterr().out
    content = GOLDEN.read_bytes()
    assert "Valid" in out
    assert "pain.001.001.03" in out
    assert "No problems found" in out
    assert f"{len(content):,} bytes" in out
    assert hashlib.sha256(content).hexdigest()[:12] in out


def write(tmp_path: Path, content: bytes, name: str = "batch.xml") -> str:
    path = tmp_path / name
    path.write_bytes(content)
    return str(path)


TX_LINE = '9 |         <PmtId><EndToEndId>E1</EndToEndId></PmtId><Amt><InstdAmt Ccy="eur">1.00</InstdAmt></Amt><Cdtr/>'


def test_an_xsd_invalid_file_exits_1_with_each_problem_under_its_source_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    content = pain001().replace(b'Ccy="EUR"', b'Ccy="eur"')

    assert main(["validate", write(tmp_path, content)]) == 1

    out = capsys.readouterr().out
    assert out.startswith("Invalid  pain.001.001.03  Transactions: 1  1 problem  Encoding: UTF-8\nbatch.xml  ")
    source = next(line for line in out.splitlines() if line.endswith(TX_LINE))
    caret, problem = out.split(f"{source}\n")[1].splitlines()[:2]
    assert caret == " " * source.index("<InstdAmt") + "^"  # no XSD column, so the caret marks the element
    assert problem.startswith("pattern_mismatch: InstdAmt attribute Ccy 'eur' on line 9 is not a currency code")


def test_a_truncated_report_counts_its_problems_as_100_plus(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    content = with_transactions(pain001(), *[BAD_CURRENCY] * 101)

    assert main(["validate", write(tmp_path, content)]) == 1

    out = capsys.readouterr().out
    assert out.startswith("Invalid  pain.001.001.03  Transactions: 102  100+ problems  Encoding: UTF-8\n")
    assert out.count("pattern_mismatch: ") == 100


def test_a_truncated_markdown_report_counts_its_problems_as_100_plus(tmp_path: Path) -> None:
    content = with_transactions(pain001(), *[BAD_CURRENCY] * 101)
    output = tmp_path / "report.md"

    assert main(["validate", write(tmp_path, content), "--output-file", str(output)]) == 1

    assert "\n| Problems | 100+ |\n" in output.read_text(encoding="utf-8")


def test_line_separators_other_than_newlines_do_not_shift_source_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # lxml counts only \n, \r\n and \r as line breaks; U+2028 and U+0085 stay inside line 2.
    content = (
        pain001()
        .replace(b'Ccy="EUR"', b'Ccy="eur"')
        .replace(b"<Document", "<!-- a\u2028b\u0085c -->\n<Document".encode(), 1)
    )
    output = tmp_path / "report.md"

    assert main(["validate", write(tmp_path, content)]) == 1
    assert main(["validate", write(tmp_path, content), "--output-file", str(output)]) == 1

    assert f"10 | {TX_LINE[4:]}\n" in capsys.readouterr().out
    assert f"  10 | {TX_LINE[4:]}\n" in output.read_text(encoding="utf-8")


def test_the_caret_marks_the_problem_element_not_a_longer_tag_that_starts_the_same(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    content = pain001().replace(b'<InstdAmt Ccy="EUR">', b'<!-- <InstdAmtX --><InstdAmt Ccy="eur">')

    assert main(["validate", write(tmp_path, content)]) == 1

    out = capsys.readouterr().out
    source = next(line for line in out.splitlines() if "<!-- <InstdAmtX -->" in line)
    caret = out.split(f"{source}\n")[1].splitlines()[0]
    assert caret == " " * source.index("<InstdAmt ") + "^"


def test_problems_are_listed_by_line_in_both_reports(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # The XSD reports PmtInf's missing child (line 5) after the bad IBAN inside it (line 7).
    content = pain001().replace(b"DE89370400440532013000", b"xx")
    content = re.sub(rb"      <CdtTrfTxInf>.*?</CdtTrfTxInf>\n", b"", content, flags=re.DOTALL)
    output = tmp_path / "report.md"

    assert main(["validate", write(tmp_path, content)]) == 1
    assert main(["validate", write(tmp_path, content), "--output-file", str(output)]) == 1

    out = capsys.readouterr().out
    assert out.index("missing_element: ") < out.index("pattern_mismatch: ")
    report = output.read_text(encoding="utf-8")
    assert report.index("**missing_element** at 5") < report.index("**pattern_mismatch** at 7")


@pytest.mark.parametrize(
    ("make", "error"),
    [
        (lambda tmp: str(tmp / "nope.xml"), "cannot read"),
        (lambda tmp: write(tmp, b""), "is empty"),
        (lambda tmp: write(tmp, b" " * (10 * 1024 * 1024 + 1)), "is over 10 MB"),
        (lambda tmp: str(tmp), "cannot read"),  # a folder
    ],
    ids=["missing", "empty", "over-10-mb", "folder"],
)
def test_an_unusable_input_exits_2_with_one_line_on_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], make: Callable[[Path], str], error: str
) -> None:
    assert main(["validate", make(tmp_path)]) == 2

    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("pain: ")
    assert error in err
    assert err.count("\n") == 1


def test_a_missing_output_folder_exits_2_and_is_not_created(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "missing" / "report.md"

    assert main(["validate", str(GOLDEN), "--output-file", str(output)]) == 2

    assert capsys.readouterr().err == f"pain: the output folder {output.parent} does not exist\n"
    assert not output.parent.exists()


def test_a_usage_error_exits_2_with_one_line_on_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_:
        main(["validate"])

    assert exit_.value.code == 2
    assert capsys.readouterr().err == "pain: the following arguments are required: file\n"


def test_a_malformed_file_exits_1_and_points_at_the_broken_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    content = b'<?xml version="1.0"?>\n<Document>\n  <CstmrCdtTrfInitn>\n</Document>\n'

    assert main(["validate", write(tmp_path, content)]) == 1

    out = capsys.readouterr().out
    assert out.startswith("Invalid  unknown Message Version  Transactions: unknown  1 problem  Encoding: unknown\n")
    assert "4 | </Document>\n" in out
    assert "malformed_xml: The file is not well-formed XML" in out


def test_a_doctype_is_shown_on_its_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    content = pain001().replace(b"<Document", b"<!DOCTYPE Document>\n<Document", 1)

    assert main(["validate", write(tmp_path, content)]) == 1

    assert "2 | <!DOCTYPE Document>\ndtd_not_allowed: " in capsys.readouterr().out


def test_a_problem_without_a_line_is_listed_by_its_message(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    content = pain001().replace(b"</CstmrCdtTrfInitn>", b"<a/>" * 500_001 + b"</CstmrCdtTrfInitn>")

    assert main(["validate", write(tmp_path, content)]) == 1

    assert capsys.readouterr().out.endswith(
        "\n\ntoo_many_elements: The file has 500,024 elements; the limit is 500,000\n"
    )


def test_a_problem_without_a_line_is_listed_after_the_blocks_in_markdown(tmp_path: Path) -> None:
    content = pain001().replace(b"</CstmrCdtTrfInitn>", b"<a/>" * 500_001 + b"</CstmrCdtTrfInitn>")
    output = tmp_path / "report.md"

    assert main(["validate", write(tmp_path, content), "--output-file", str(output)]) == 1

    assert output.read_text(encoding="utf-8").endswith(
        "## Problems\n\n### Not tied to a line\n\n"
        "- **too_many_elements**: The file has 500,024 elements; the limit is 500,000\n"
    )


def test_a_valid_file_overwrites_the_output_file_with_a_markdown_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "report.md"
    output.write_text("old report")

    assert main(["validate", str(GOLDEN), "--output-file", str(output)]) == 0

    assert capsys.readouterr().out == f"Valid  pain.001.001.03  0 problems\nReport written to {output}\n"
    content = GOLDEN.read_bytes()
    assert output.read_bytes().decode() == (
        "# pain.001.001.03.xml\n"
        "\n"
        "| | |\n"
        "|---|---|\n"
        "| Result | Valid |\n"
        "| Message Version | pain.001.001.03 |\n"
        "| Transactions | 10 |\n"
        "| Problems | 0 |\n"
        "| Encoding | UTF-8 |\n"
        f"| Size | {len(content):,} bytes |\n"
        f"| sha256 | {hashlib.sha256(content).hexdigest()} |\n"
        "\n"
        "No problems found\n"
    )


def test_problems_whose_windows_overlap_share_one_code_block(tmp_path: Path) -> None:
    # Problems on lines 9 and 12: windows 7 to 11 and 10 to 14 merge.
    content = with_transactions(pain001().replace(b'Ccy="EUR"', b'Ccy="eur"'), BAD_CURRENCY)
    output = tmp_path / "report.md"

    assert main(["validate", write(tmp_path, content), "--output-file", str(output)]) == 1

    report = output.read_text(encoding="utf-8")
    lines = content.decode().splitlines()
    window = "".join(f"  {n:>2} | {lines[n - 1]}\n" for n in range(7, 15))
    assert report.count("### ") == 1
    assert "## Problems\n\n### Lines 7 to 14\n\n- **pattern_mismatch** at 9: InstdAmt attribute Ccy 'eur'" in report
    assert "- **pattern_mismatch** at 12: " in report
    assert "  `/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf[2]/Amt/InstdAmt`\n" in report
    assert (
        "  <details><summary>cause</summary>Element '{urn:iso:std:iso:20022:tech:xsd:pain.001.001.03}InstdAmt'"
        in report
    )
    assert report.endswith(f"\n```xml\n{window}```\n")


def test_a_backtick_run_in_the_source_cannot_close_the_fence(tmp_path: Path) -> None:
    content = pain001().replace(b'Ccy="EUR"', b'Ccy="eur"').replace(b"<Cdtr/>", b"<Cdtr/><!-- ```` -->")
    output = tmp_path / "report.md"

    assert main(["validate", write(tmp_path, content), "--output-file", str(output)]) == 1

    report = output.read_text(encoding="utf-8")
    assert "\n`````xml\n" in report
    assert report.endswith("<Cdtr/><!-- ```` -->\n  10 |       </CdtTrfTxInf>\n  11 |     </PmtInf>\n`````\n")
