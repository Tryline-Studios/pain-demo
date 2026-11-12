"""The resolved Sample File model: what the renderer turns into XML (spec 10.2).

The ISO rules the XSD cannot express are unrepresentable here (spec 10.3): Ultimate Debtor exists only on a
Transaction, and Intermediary Agents are a tuple, so they are always contiguous from 1.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from pain_demo.generation.request import CurrencyCode, MessageVersion


@dataclass(frozen=True)
class Address:
    street: str
    building_number: str
    post_code: str
    town: str
    country: str


@dataclass(frozen=True)
class ListedAddress:
    """A Listing's address as the list gives it: free lines, rendered unstructured (spec 6.9)."""

    lines: tuple[str, ...]
    country: str


@dataclass(frozen=True)
class Party:
    name: str
    address: Address | ListedAddress | None = None


@dataclass(frozen=True)
class Agent:
    bic: str | None
    """None renders the agent by name and address only (`name_only`)."""
    name: str | None
    """None renders the BIC alone (`bic_only`)."""
    routing_number: str | None = None
    """The ABA routing number of a US agent, rendered as its clearing system member id."""
    lei: str | None = None
    """`FinInstnId/LEI`, which exists from .09: a Hit leaves it None before then rather than have the build drop it."""
    address: ListedAddress | None = None


@dataclass(frozen=True)
class Iban:
    iban: str


@dataclass(frozen=True)
class OtherAccount:
    """`Othr/Id`: a US account number, or a synthetic one where the country has no IBAN (spec 6.9)."""

    id: str


type Account = Iban | OtherAccount


@dataclass(frozen=True)
class Remittance:
    unstructured: str | None = None
    creditor_reference: str | None = None
    """An ISO 11649 `RF` creditor reference, rendered as structured remittance."""
    additional: str | None = None
    """`Strd/AddtlRmtInf`; with the invoicer and invoicee it shares the one `Strd` block."""
    invoicer: str | None = None
    """`Strd/Invcr/Nm`."""
    invoicee: str | None = None
    """`Strd/Invcee/Nm`."""


@dataclass(frozen=True)
class Transaction:
    end_to_end_id: str
    amount: Decimal
    currency: CurrencyCode
    creditor: Party
    creditor_agent: Agent
    creditor_account: Account
    remittance: Remittance
    ultimate_debtor: Party | None = None
    ultimate_creditor: Party | None = None
    intermediary_agents: tuple[()] | tuple[Agent] | tuple[Agent, Agent] | tuple[Agent, Agent, Agent] = ()


@dataclass(frozen=True)
class SampleFileModel:
    """One `PmtInf`: one Debtor, Debtor Agent and Debtor account per file. The Debtor is also `GrpHdr/InitgPty`."""

    message_version: MessageVersion
    message_id: str
    created_at: datetime
    execution_date: date
    payment_information_id: str
    debtor: Party
    debtor_account: Account
    debtor_agent: Agent
    transactions: tuple[Transaction, ...]
