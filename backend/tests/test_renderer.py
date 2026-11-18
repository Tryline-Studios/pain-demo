"""The renderer seam (spec 10.2 and 10.4): our resolved Sample File model in, XML bytes and build drops out."""

import re
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest
from sample_files import assert_valid_sample_file

from pain_workbench import renderer
from pain_workbench.generation.model import (
    Address,
    Agent,
    Iban,
    OtherAccount,
    Party,
    Remittance,
    SampleFileModel,
    Transaction,
)
from pain_workbench.renderer import RenderFailed, render
from pain_workbench.validation import MESSAGE_VERSIONS


def address(country: str) -> Address:
    return Address(street="Mudeweg", building_number="4", postcode="06690", town="Gross-Gerau", country=country)


DEBTOR = Party(name="Karsten Wieloch GmbH", address=address("DE"))

MODEL = SampleFileModel(
    message_version="pain.001.001.09",
    message_id="MSG-0123456789AB",
    created_at=datetime.fromisoformat("2026-11-12T09:30:00+00:00"),
    execution_date=datetime(2026, 11, 13).date(),
    payment_information_id="PMT-0123456789AB",
    debtor=DEBTOR,
    debtor_account=Iban("DE89370400440532013000"),
    debtor_agent=Agent(bic="COBADEFFXXX", name="Commerzbank"),
    transactions=(
        Transaction(
            end_to_end_id="E2E-1",
            amount=Decimal("1234.50"),
            currency="EUR",
            creditor_agent=Agent(bic="BNPAFRPP", name="BNP Paribas"),
            creditor=Party(name="Roland Salmon", address=address("FR")),
            creditor_account=Iban("FR7630006000011234567890189"),
            ultimate_debtor=Party(name="Ruth Baker"),
            ultimate_creditor=Party(name="Lucas Barroso"),
            intermediary_agents=(Agent(bic="DEUTDEFF", name="Deutsche Bank"),),
            remittance=Remittance(creditor_reference="RF18539007547034"),
        ),
        Transaction(
            end_to_end_id="E2E-2",
            amount=Decimal("10.00"),
            currency="USD",
            creditor_agent=Agent(bic="CHASUS33", name="JPMorgan Chase", routing_number="021000021"),
            creditor=Party(name="Ryan Gallagher", address=address("US")),
            creditor_account=OtherAccount("123456789"),
            remittance=Remittance(unstructured=("Invoice 4711",)),
        ),
    ),
)


@pytest.mark.parametrize("message_version", MESSAGE_VERSIONS)
def test_every_role_renders_valid_in_every_message_version(message_version: str) -> None:
    rendered = render(replace(MODEL, message_version=message_version))

    assert_valid_sample_file(rendered.xml, message_version)
    assert rendered.dropped == []
    assert b"<MsgId>MSG-0123456789AB</MsgId>" in rendered.xml
    assert b"<EndToEndId>E2E-2</EndToEndId>" in rendered.xml


def test_the_initiating_party_is_the_debtor() -> None:
    xml = render(MODEL).xml.decode()

    initiating_party = xml[xml.index("<InitgPty>") : xml.index("</InitgPty>")]
    assert "<Nm>Karsten Wieloch GmbH</Nm>" in initiating_party


def test_output_the_xsd_refuses_fails_the_build_with_the_xsd_message() -> None:
    too_long = replace(MODEL, debtor=Party(name="N" * 141, address=address("DE")))

    with pytest.raises(RenderFailed, match=r"Dbtr/Nm: value length cannot be greater than 140"):
        render(too_long)


def test_an_element_the_message_version_cannot_hold_is_dropped_and_reported() -> None:
    with_lei = replace(MODEL, debtor_agent=Agent(bic="COBADEFFXXX", name="Commerzbank", lei="851WYGNLUQLFZBSYGB56"))

    assert render(replace(with_lei, message_version="pain.001.001.09")).dropped == []
    rendered = render(replace(with_lei, message_version="pain.001.001.03"))

    assert rendered.dropped == ["/Document/CstmrCdtTrfInitn/PmtInf/DbtrAgt/FinInstnId/LEI"]
    assert b"851WYGNLUQLFZBSYGB56" not in rendered.xml
    assert_valid_sample_file(rendered.xml, "pain.001.001.03")


@pytest.mark.parametrize(
    ("dropped", "carries_a_placement"),
    [
        ("/Document/CstmrCdtTrfInitn/PmtInf/DbtrAgt/FinInstnId/LEI", False),
        ("/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/Cdtr/PstlAdr/BldgNm", False),
        ("/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/Cdtr/Nm", True),
        ("/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/CdtrAgt/FinInstnId/BICFI", True),
        ("/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/IntrmyAgt2", True),
        ("/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/RmtInf/Ustrd", True),
        ("/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/RmtInf/Strd/Invcr/Nm", True),
        ("/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/RmtInf/Strd/Invcr/PstlAdr/Ctry", False),
    ],
)
def test_a_dropped_element_that_can_carry_a_placement_is_a_build_failure(
    monkeypatch: pytest.MonkeyPatch, dropped: str, carries_a_placement: bool
) -> None:
    real_build = renderer.build

    def build_that_drops(scenario: dict, version: str) -> object:
        result = real_build(scenario, version)
        result.report.dropped.append(dropped)
        return result

    # No model of ours makes pain001 drop a Placement, so the drop is injected at the pain001 boundary.
    monkeypatch.setattr(renderer, "build", build_that_drops)

    if carries_a_placement:
        with pytest.raises(RenderFailed, match=re.escape(f"{dropped} dropped in pain.001.001.09")):
            render(MODEL)
    else:
        assert render(MODEL).dropped == [dropped]
