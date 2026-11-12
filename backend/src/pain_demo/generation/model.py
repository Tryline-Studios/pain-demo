"""The resolved Sample File model: what the renderer turns into XML (spec 10.2).

The ISO rules the XSD cannot express are unrepresentable here (spec 10.3): Ultimate Debtor exists only on a
Transaction, and Intermediary Agents are a tuple, so they are always contiguous from 1.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Address:
    street: str
    building_number: str
    post_code: str
    town: str
    country: str


@dataclass(frozen=True)
class Party:
    name: str
    address: Address | None = None


@dataclass(frozen=True)
class Agent:
    bic: str
    name: str
    routing_number: str | None = None
    """The ABA routing number of a US agent, rendered as its clearing system member id."""
    lei: str | None = None
    """`FinInstnId/LEI`, which .03 to .08 cannot hold: the build drops it there with an Answer Key warning."""


@dataclass(frozen=True)
class Iban:
    iban: str


@dataclass(frozen=True)
class OtherAccount:
    """`Othr/Id`: a US account number."""

    id: str


type Account = Iban | OtherAccount


@dataclass(frozen=True)
class Remittance:
    unstructured: str | None = None
    creditor_reference: str | None = None
    """An ISO 11649 `RF` creditor reference, rendered as structured remittance."""


@dataclass(frozen=True)
class Transaction:
    end_to_end_id: str
    amount: Decimal
    currency: str
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

    message_version: str
    message_id: str
    created_at: datetime
    execution_date: date
    payment_information_id: str
    debtor: Party
    debtor_account: Account
    debtor_agent: Agent
    transactions: tuple[Transaction, ...]
