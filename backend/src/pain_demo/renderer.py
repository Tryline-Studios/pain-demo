"""The pain001 boundary (spec 10.2): the only module that imports pain001.

`render` maps our resolved Sample File model to a `pain001.corpus.build` scenario, passing every identifier
explicitly, and returns the XML bytes plus the elements the version fitter dropped. It is blocking: callers run it
in a worker thread.
"""

import importlib.resources
import re
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


def xsd(message_version: str) -> etree._Element:
    """pain001's bundled XSD document for a Message Version (pain.001.001.03 to .13), freshly parsed."""
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
    scenario: dict[str, Any] = {"name": party.name}
    if party.address:
        scenario["address"] = _address(party.address)
    if party.id:
        scenario["id"] = {"org": {"other": [_other_id(party.id.other_id, party.id.scheme)]}}
    if party.country_of_residence:
        scenario["country_of_residence"] = party.country_of_residence
    return scenario


def _address(address: Address | ListedAddress) -> dict[str, Any]:
    if isinstance(address, ListedAddress):
        return _present({"form": "unstructured", "lines": list(address.lines), "country": address.country})
    return _present(
        {
            "form": "structured",
            "street": address.street,
            "building_number": address.building_number,
            "building_name": address.building_name,
            "floor": address.floor,
            "post_box": address.post_box,
            "room": address.room,
            "post_code": address.postcode,
            "town": address.town,
            "town_location": address.town_location_name,
            "district": address.district_name,
            "country_subdivision": address.country_subdivision,
            "country": address.country,
        }
    )


def _present(scenario: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in scenario.items() if value is not None}


def _other_id(identifier: str, scheme: str | None) -> dict[str, str]:
    return _present({"id": identifier, "scheme": scheme})


def _agent(agent: Agent) -> dict[str, Any]:
    scenario: dict[str, Any] = {"name": agent.name} if agent.name else {}  # None is `bic_only` (spec 6.6)
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
    return {"other": _other_id(account.id, account.scheme)}


def _remittance(remittance: Remittance) -> dict[str, Any]:
    scenario: dict[str, Any] = {}
    if remittance.unstructured:
        scenario["unstructured"] = list(remittance.unstructured)
    structured = {
        "creditor_reference": remittance.creditor_reference and {"reference": remittance.creditor_reference},
        "invoicer": remittance.invoicer and {"name": remittance.invoicer},
        "invoicee": remittance.invoicee and {"name": remittance.invoicee},
        "additional": list(remittance.additional),
    }
    if structured := {key: value for key, value in structured.items() if value}:
        scenario["structured"] = [structured]
    return scenario
