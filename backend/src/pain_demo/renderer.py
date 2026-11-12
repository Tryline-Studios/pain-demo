"""The pain001 boundary (spec 10.2): the only module that imports pain001.

`render` maps our resolved Sample File model to a `pain001.corpus.build` scenario, passing every identifier
explicitly, and returns the XML bytes plus the elements the version fitter dropped. It is blocking: callers run it
in a worker thread.
"""

import importlib.resources
import re
import threading
from dataclasses import asdict, dataclass
from typing import Any

import pain001
import structlog
from lxml import etree
from pain001.corpus import BuildError, ScenarioError, build

from pain_demo.generation.model import (
    Account,
    Address,
    Agent,
    Iban,
    ListedAddress,
    Party,
    Remittance,
    SampleFileModel,
    Transaction,
)

_SCENARIO_ID = "xx.pain-demo.sample-file"
"""corpus.build requires a scenario id; it never reaches the output because every identifier is explicit."""

log = structlog.get_logger("pain_demo.renderer")

_PLACEMENT_ELEMENTS = re.compile(
    r"Nm|BIC|BICFI|FinInstnId|Ustrd|AddtlRmtInf|Invcr|Invcee|RmtInf|Strd"
    r"|InitgPty|Dbtr|DbtrAgt|Cdtr|CdtrAgt|UltmtDbtr|UltmtCdtr|IntrmyAgt[1-3]"
)
"""Element names that carry a Placement, or contain one: dropping any of them would falsify the Answer Key."""


class RenderFailed(Exception):
    """The output failed the XSD or lost a Placement (spec 10.4); `messages` say why."""

    def __init__(self, messages: list[str]) -> None:
        super().__init__(" | ".join(messages))
        self.messages = messages


@dataclass(frozen=True)
class RenderResult:
    xml: bytes
    dropped: list[str]
    """Element paths the version fitter dropped, deduplicated, in first-seen order. None carries a Placement."""


_THREAD_SCHEMAS = threading.local()
"""Each thread's compiled schemas, by Message Version, in its `by_version` dict."""


def schema(message_version: str) -> etree.XMLSchema:
    """pain001's bundled XSD for a Message Version (pain.001.001.03 to .13), compiled once per thread and reused.

    An XMLSchema's error log belongs to the schema, not the call, so threads never share one and never wait on each
    other for it. Compiling takes about 1 ms on an idle process; see `validation._xsd_errors` for one that is not.
    """
    schemas: dict[str, etree.XMLSchema] = _THREAD_SCHEMAS.__dict__.setdefault("by_version", {})
    if message_version not in schemas:
        schemas[message_version] = etree.XMLSchema(xsd(message_version))
    return schemas[message_version]


def xsd(message_version: str) -> etree._Element:
    """pain001's bundled XSD document for a Message Version, freshly parsed."""
    path = importlib.resources.files(pain001) / "templates" / message_version / f"{message_version}.xsd"
    return etree.fromstring(path.read_bytes())


def placement_drops(dropped: list[str]) -> list[str]:
    return [path for path in dropped if _PLACEMENT_ELEMENTS.fullmatch(path.rsplit("/", 1)[-1])]


def render(model: SampleFileModel) -> RenderResult:
    scenario = _scenario(model)
    log.debug("corpus_build_scenario", scenario=scenario)  # spec 14.5: DEBUG only, it carries names
    try:
        result = build(scenario, model.message_version)
    except (BuildError, ScenarioError) as error:
        raise RenderFailed([str(error)]) from error
    log.debug("corpus_build_report", report=asdict(result.report))
    dropped = list(dict.fromkeys(result.report.dropped))
    if lost := placement_drops(dropped):
        raise RenderFailed([f"{path} dropped in {model.message_version}" for path in lost])
    return RenderResult(xml=result.xml.encode("utf-8"), dropped=dropped)


def _scenario(model: SampleFileModel) -> dict[str, Any]:
    debtor = _party(model.debtor)
    return {
        "id": _SCENARIO_ID,
        "family": "pain-demo",
        "country": model.debtor.address.country if model.debtor.address else "XX",
        "versions": [model.message_version],
        "seed": 0,
        "header": {
            "message_id": model.message_id,
            "created": model.created_at.isoformat(),
            "initiating_party": debtor,
        },
        "payment": {
            "id": model.payment_information_id,
            "method": "TRF",
            "batch_booking": False,
            "requested_execution_date": model.execution_date.isoformat(),
            "debtor": debtor,
            "debtor_account": _account(model.debtor_account),
            "debtor_agent": _agent(model.debtor_agent),
            "charge_bearer": "SLEV",
        },
        "transactions": [_transaction(tx) for tx in model.transactions],
    }


def _transaction(tx: Transaction) -> dict[str, Any]:
    scenario: dict[str, Any] = {
        "end_to_end_id": tx.end_to_end_id,
        "amount": {"ccy": tx.currency, "value": str(tx.amount)},
        "creditor_agent": _agent(tx.creditor_agent),
        "creditor": _party(tx.creditor),
        "creditor_account": _account(tx.creditor_account),
        "remittance": _remittance(tx.remittance),
    }
    if tx.ultimate_debtor:
        scenario["ultimate_debtor"] = _party(tx.ultimate_debtor)
    if tx.ultimate_creditor:
        scenario["ultimate_creditor"] = _party(tx.ultimate_creditor)
    if tx.intermediary_agents:
        scenario["intermediary_agents"] = [_agent(agent) for agent in tx.intermediary_agents]
    return scenario


def _party(party: Party) -> dict[str, Any]:
    return {"name": party.name} | ({"address": _address(party.address)} if party.address else {})


def _address(address: Address | ListedAddress) -> dict[str, Any]:
    if isinstance(address, ListedAddress):
        return {"form": "unstructured", "lines": list(address.lines), "country": address.country}
    return {
        "form": "structured",
        "street": address.street,
        "building_number": address.building_number,
        "post_code": address.post_code,
        "town": address.town,
        "country": address.country,
    }


def _agent(agent: Agent) -> dict[str, Any]:
    scenario: dict[str, Any] = {"name": agent.name}
    if agent.bic:
        scenario["bic"] = agent.bic
    if agent.routing_number:
        scenario["clearing"] = {"system": {"code": "USABA"}, "member_id": agent.routing_number}
    if agent.lei:
        scenario["lei"] = agent.lei
    if agent.address:
        scenario["address"] = _address(agent.address)
    return scenario


def _account(account: Account) -> dict[str, Any]:
    if isinstance(account, Iban):
        return {"iban": account.iban}
    return {"other": {"id": account.id}}


def _remittance(remittance: Remittance) -> dict[str, Any]:
    scenario: dict[str, Any] = {}
    if remittance.unstructured:
        scenario["unstructured"] = [remittance.unstructured]
    if remittance.creditor_reference:
        scenario["structured"] = [{"creditor_reference": {"reference": remittance.creditor_reference}}]
    return scenario
