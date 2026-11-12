"""Shared checks for every Sample File a test produces (spec 15.1)."""

import re

from lxml import etree
from pain001.corpus.rules.mdr import evaluate_mdr

from pain_demo.validation import validate_message


def assert_valid_sample_file(xml: bytes, message_version: str) -> None:
    """XSD-valid in its own Message Version via Upload Validation (spec 17.8), and the MDR second opinion agrees."""
    report = validate_message(xml, None)
    assert report.problems == []
    assert report.valid
    assert report.message_version == message_version
    assert evaluate_mdr(xml.decode("utf-8")) == []


def resolve(document: etree._Element, xpath: str) -> list[etree._Element]:
    """The elements at an Answer Key XPath such as `/Document/.../CdtTrfTxInf[3]/Cdtr/Nm`, whatever the namespace."""
    steps = re.sub(r"([A-Za-z0-9]+)(\[\d+\])?", lambda m: f"*[local-name()='{m[1]}']{m[2] or ''}", xpath)
    return document.xpath(steps)
