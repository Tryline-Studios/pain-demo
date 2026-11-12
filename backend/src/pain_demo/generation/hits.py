"""Drawn Hits (spec 6, 7): Sanctioned Entities placed into a clean Sample File model, and the Answer Key entries
that say where each one is (spec 11.3, 11.4).

The clean model is drawn first and Hits are overlaid from their own streams (`hits/placement`, then `hits/<k>` per
Hit), so Hit Count 0 leaves the file untouched and adding a Hit never reshuffles an innocent row (spec 9.3).
"""

import random
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from typing import Literal, cast

from pydantic import MISSING, BaseModel, Field, JsonValue
from schwifty import BIC

from pain_demo.catalogue import Catalogue
from pain_demo.catalogue.capabilities import (
    CONTROLLER_PLACEMENTS,
    FILE_LEVEL_PLACEMENTS,
    PLACEMENT_ELIGIBILITY,
    VERBATIM_SOURCES,
    NameVariant,
    Placement,
    candidate_names,
    supported_name_variants,
    transliterations,
)
from pain_demo.catalogue.schema import (
    Address as CatalogueAddress,
)
from pain_demo.catalogue.schema import (
    Bank,
    Bic,
    Entity,
    EntityType,
    Individual,
    ListingRef,
    Name,
    NameSourceType,
    SanctionsList,
    Script,
)
from pain_demo.catalogue.transliteration import TransliterationScheme
from pain_demo.generation.exposure_countries import EXPOSURE_COUNTRIES
from pain_demo.generation.fuzz import FuzzOperation, fuzz
from pain_demo.generation.generated_data import GeneratedData, digits
from pain_demo.generation.model import (
    Account,
    Agent,
    ListedAddress,
    Party,
    SampleFileModel,
    Transaction,
)
from pain_demo.generation.named_hits import HitsInvalid, check, controllers, error, placement_options
from pain_demo.generation.request import EffectiveRequest, NamedHit, RenderingMode
from pain_demo.generation.seeds import stream
from pain_demo.generation.supplied import SuppliedRemittance, SuppliedStructuredRemittance, creditor_side_supplied
from pain_demo.identifiers import bic_country


@dataclass(frozen=True)
class PlacementRule:
    """What generation knows about one Placement; who may take it is `PLACEMENT_ELIGIBILITY` (spec 6.1)."""

    name_path: str
    """The `Nm` element, under `PmtInf` for a file-level Placement and under `CdtTrfTxInf[n]` otherwise."""
    agent: bool = False
    file_level: bool = False
    party_weight: float = 0
    """Drawn for a Corporate or Individual (spec 6.5)."""
    bank_weight: float = 0
    """Drawn for a Bank (spec 6.5)."""


_PARTY_WEIGHTS: dict[Placement, float] = {"creditor": 35, "ultimate_creditor": 15, "ultimate_debtor": 15, "debtor": 10}


def _bank_party_role(placement: Placement) -> float:
    """A Bank's "party roles 10", which the spec does not split: shared over the party roles as for a party."""
    return 10 * _PARTY_WEIGHTS[placement] / sum(_PARTY_WEIGHTS.values())


def _party(placement: Placement, name_path: str, *, file_level: bool = False) -> PlacementRule:
    weight = _PARTY_WEIGHTS[placement]
    return PlacementRule(name_path, file_level=file_level, party_weight=weight, bank_weight=_bank_party_role(placement))


PLACEMENTS: dict[Placement, PlacementRule] = {
    "creditor_agent": PlacementRule("CdtrAgt/FinInstnId/Nm", agent=True, bank_weight=40),
    # The Intermediary Agent's 30 shared by the slot weights 60/30/10.
    "intermediary_agent_1": PlacementRule("IntrmyAgt1/FinInstnId/Nm", agent=True, bank_weight=30 * 60 / 100),
    "intermediary_agent_2": PlacementRule("IntrmyAgt2/FinInstnId/Nm", agent=True, bank_weight=30 * 30 / 100),
    "intermediary_agent_3": PlacementRule("IntrmyAgt3/FinInstnId/Nm", agent=True, bank_weight=30 * 10 / 100),
    "debtor_agent": PlacementRule("DbtrAgt/FinInstnId/Nm", agent=True, file_level=True, bank_weight=15),
    "creditor": _party("creditor", "Cdtr/Nm"),
    "ultimate_creditor": _party("ultimate_creditor", "UltmtCdtr/Nm"),
    "ultimate_debtor": _party("ultimate_debtor", "UltmtDbtr/Nm"),
    "debtor": _party("debtor", "Dbtr/Nm", file_level=True),
    # The name path is the element's, drawn per Hit; `RmtInf` only orders it among its transaction's Hits.
    "remittance": PlacementRule("RmtInf", party_weight=25, bank_weight=5),
}
"""Every drawn Placement, in draw order: the order feeds `choices`, so changing it changes every Seed's Hits."""
type RemittanceElement = Literal["ustrd", "addtl_rmt_inf", "invcr", "invcee"]
REMITTANCE_ELEMENTS: dict[RemittanceElement, tuple[str, float]] = {
    "ustrd": ("RmtInf/Ustrd", 70),
    "addtl_rmt_inf": ("RmtInf/Strd/AddtlRmtInf", 15),
    "invcr": ("RmtInf/Strd/Invcr/Nm", 7.5),  # "Invcr or Invcee 15", split evenly
    "invcee": ("RmtInf/Strd/Invcee/Nm", 7.5),
}
"""Where a remittance mention goes, with its path under `CdtTrfTxInf[n]` and its weight (spec 6.5, 6.7)."""
_REMITTANCE_FIELDS: dict[RemittanceElement, str] = {
    "ustrd": "unstructured",
    "addtl_rmt_inf": "additional",
    "invcr": "invoicer",
    "invcee": "invoicee",
}
_REMITTANCE_LISTS = frozenset({"unstructured", "additional"})
REMITTANCE_SENTENCES = (
    "Invoice {n} payment to {name}",
    "Payment for order {n}, supplier {name}",
    "Settlement of contract {n} with {name}",
    "Consulting fees ref {n} - {name}",
    "{name} invoice {n}",
)
"""Seeded sentences around the rendered name in `Ustrd` and `AddtlRmtInf` (spec 6.7)."""
_MAX_TEXT = 140
NAME_VARIANT_WEIGHTS: dict[NameVariant, float] = {
    "exact": 40,
    "alias": 25,
    "fuzzed": 20,
    "transliteration": 10,
    "native_script": 5,
}
"""Spec 6.5, in draw order: the order feeds `choices`, so changing it changes every Seed's names."""
_PMT_INF = "/Document/CstmrCdtTrfInitn/PmtInf"
_FIRST_WITH_BICFI = 4
_FIRST_WITH_AGENT_LEI = 9
"""`FinInstnId/LEI` exists from .09; earlier versions get no LEI rather than a dropped one."""


def placement_weights(entity_type: EntityType) -> dict[Placement, float]:
    """The default Placement draw for an Entity Type (spec 6.5), over the Placements it is eligible for."""
    return {
        placement: rule.bank_weight if entity_type == "bank" else rule.party_weight
        for placement, rule in PLACEMENTS.items()
        if entity_type in PLACEMENT_ELIGIBILITY[placement]
    }


def _absent(value: object) -> bool:
    return value is None


class NameSource(BaseModel):
    value: str
    type: NameSourceType
    script: Script
    listing: ListingRef


class HitName(BaseModel):
    variant: NameVariant
    rendered: str
    """Exactly as it appears in the XML."""
    source: NameSource
    """The listed name it comes from: the Cyrillic name of a transliteration, the base of a fuzz."""
    scheme: TransliterationScheme | None = Field(default=None, exclude_if=_absent, description="Transliteration only")
    base: str | None = Field(default=None, exclude_if=_absent, description="Fuzzed only: the listed name altered")
    operations: list[FuzzOperation] | None = Field(
        default=None, exclude_if=_absent, description="Fuzzed only: the operations, in the order applied"
    )


class HitBic(BaseModel):
    value: str
    source: Literal["listing", "gleif"]


class HitEntity(BaseModel):
    id: str
    entity_type: EntityType
    listings: list[ListingRef]


class Trigger(BaseModel):
    kind: Literal["name", "bic", "lei"]
    value: str
    listed_on: list[SanctionsList]
    """The lists that carry this value: a name case-insensitively, a BIC only on its Listing, an LEI on none."""


class Displaced(BaseModel):
    field: str
    """The dotted request path of the supplied value, e.g. `transactions[2].creditor`."""
    value: JsonValue
    """As supplied: an object for a party or agent, a string or list for a remittance element, null if left out."""


class Hit(BaseModel):
    """One Placement of a Sanctioned Entity (spec 11.3), in wire order."""

    id: str
    scope: Literal["file", "transaction"]
    transaction_number: int | None = Field(default=None, exclude_if=_absent, description="Absent for scope file")
    end_to_end_id: str | None = Field(default=None, exclude_if=_absent, description="Absent for scope file")
    xpath: str
    entity: HitEntity
    placement: Placement
    element: RemittanceElement | None = Field(default=None, exclude_if=_absent, description="Remittance only")
    rendering_mode: RenderingMode | None = Field(default=None, exclude_if=_absent, description="Agents only")
    name: HitName | None
    bic: HitBic | None
    lei: str | None
    address_from_listing: str | None
    """The `entry_id` of the Listing whose address the Placement carries."""
    triggers: list[Trigger]
    origin: Literal["named", "drawn"]
    paired_with: str | None
    """The other half of a `with_controller` pair (spec 6.8); drawn Hits never pair."""
    displaced: Displaced | None
    """The Supplied Data this Hit replaced (spec 5.3, 11.4)."""


@dataclass(frozen=True)
class _Planned:
    entity: Entity
    placement: Placement
    transaction: int | None = None
    stream: str = ""
    """The Hit's own randomness: `hits/<k>` for the k-th drawn Hit, `hits/named/<i>` for named Hit i."""
    origin: Literal["named", "drawn"] = "drawn"
    name_variant: NameVariant | None = None
    rendering_mode: RenderingMode | None = None
    pair: int | None = None
    """The index of the other half of a `with_controller` pair (spec 6.8)."""


def draw(request: EffectiveRequest, catalogue: Catalogue) -> list[_Planned]:
    """Named Hits first, then the drawn ones: Entities, Placements and transaction numbers, all from the placement
    stream (spec 6.3, 6.5), constrained by the allowlists and kept off what the named Hits took.

    Every valid Hit Count succeeds without allowlists: once the Hits left outnumber the free transactions, the Hit
    must go to a free file-level Placement, and a Hit that can only take the Debtor Agent goes to the next Bank in
    the queue. Allowlists that leave a drawn Hit nowhere to go are a validation error.
    """
    check(request, catalogue)
    named = _plan_named(request, catalogue)
    rng = stream(request.seed, "hits/placement")
    allowed = set(request.name_variants or NAME_VARIANT_WEIGHTS)
    entities = [e for e in catalogue.entities.values() if allowed & set(supported_name_variants(e))]
    queue: list[Entity] = []
    # Each Hit draws a distinct Entity until the catalogue is exhausted, the named Hits' included (spec 6.3).
    unused = {p.entity.id for p in named}
    taken: set[Placement] = {p.placement for p in named if p.transaction is None}
    used = {p.transaction for p in named if p.transaction is not None}
    # Exposures take transactions no Hit touches and no row supplies a creditor side for (spec 5.3, 8.2).
    exposable = set(range(1, request.transaction_count + 1)) - used - creditor_side_supplied(request.transactions)
    if request.exposure_count > len(exposable):
        held = len(creditor_side_supplied(request.transactions) - used)
        msg = (
            f"exposure_count must not exceed the {len(exposable)} transactions left free: named Hits take {len(used)}"
            f" and {held} carry a supplied creditor side, which an Exposure never replaces"
        )
        raise HitsInvalid([error("exposure_count", msg=msg)])
    free_transactions = request.transaction_count - request.exposure_count - len(used)
    count = request.hit_count - len(named)
    planned: list[_Planned] = []
    for drawn in range(count):
        forced = count - drawn > free_transactions
        # Without the Exposures this Hit would have had a transaction: say so if it ends up nowhere.
        crowded = forced and count - drawn <= free_transactions + request.exposure_count

        def weights(entity: Entity, *, forced: bool = forced) -> dict[Placement, float]:
            # Leaving taken file-level Placements out is the spec's "redrawn", without the loop.
            table = placement_weights(entity.entity_type)
            return {
                p: w
                for p, w in table.items()
                if p not in taken
                and (PLACEMENTS[p].file_level or not forced)
                and (request.placements is None or p in request.placements)
            }

        try:
            entity = _next_entity(queue, entities, unused, rng, lambda entity: bool(weights(entity)))
        except HitsInvalid:
            if not crowded:
                raise
            msg = "the drawn Hits cannot all be placed: the exposure_count Exposures take the transactions they need"
            raise HitsInvalid([error("hit_count", msg=msg)]) from None
        options = weights(entity)
        (placement,) = rng.choices(list(options), weights=list(options.values()))
        if PLACEMENTS[placement].file_level:
            taken.add(placement)
        else:
            free_transactions -= 1
        planned.append(_Planned(entity, placement, stream=f"hits/{drawn + 1}"))
    transaction_level = sum(not PLACEMENTS[plan.placement].file_level for plan in planned)
    free = [n for n in range(1, request.transaction_count + 1) if n not in used]
    if request.transactions:
        numbers = _prefer_generated(
            request, [p.placement for p in planned if not PLACEMENTS[p.placement].file_level], free, exposable, rng
        )
    else:
        numbers = iter(rng.sample(free, transaction_level))
    planned = [p if PLACEMENTS[p.placement].file_level else replace(p, transaction=next(numbers)) for p in planned]
    return _debtor_agent_at_home([*named, *planned], list(catalogue.entities.values()), rng, request)


def _plan_named(request: EffectiveRequest, catalogue: Catalogue) -> list[_Planned]:
    """What each named Hit leaves out is drawn from `hits/named`; unpinned transactions avoid the pinned ones."""
    rng = stream(request.seed, "hits/named")
    pinned = {hit.transaction for hit in request.hits if hit.transaction is not None}
    taken = {hit.placement for hit in request.hits if hit.placement in FILE_LEVEL_PLACEMENTS}
    free = [n for n in range(1, request.transaction_count + 1) if n not in pinned]
    rng.shuffle(free)
    planned: list[_Planned] = []
    for index, hit in enumerate(request.hits):
        entity = catalogue.entities[hit.entity]

        def needs(placement: Placement, hit: NamedHit = hit) -> int:
            """Free transactions this Placement would use: its own, or the Ultimate Debtor beside a Debtor."""
            if placement in FILE_LEVEL_PLACEMENTS:
                return int(hit.with_controller)
            return int(hit.transaction is None)

        placement = hit.placement
        if placement is None:
            table = placement_weights(entity.entity_type)
            options = {p: table[p] for p in placement_options(hit, entity) if p not in taken and needs(p) <= len(free)}
            if not options:
                msg = f"{entity.id}: no Placement is left free for this Hit"
                raise HitsInvalid([error("hits", index, "placement", msg=msg)])
            (placement,) = rng.choices(list(options), weights=list(options.values()))
            if placement in FILE_LEVEL_PLACEMENTS:
                taken.add(placement)
        elif needs(placement) > len(free):
            msg = f"{entity.id}: no transaction is left free for this Hit"
            raise HitsInvalid([error("hits", index, "transaction", msg=msg)])
        file_level = placement in FILE_LEVEL_PLACEMENTS
        transaction = None if file_level else hit.transaction or free.pop()
        plan = _Planned(
            entity,
            placement,
            transaction,
            stream=f"hits/named/{index + 1}",
            origin="named",
            name_variant=hit.name_variant,
            rendering_mode=hit.rendering_mode,
        )
        if not hit.with_controller:
            planned.append(plan)
            continue
        controller = catalogue.entities[rng.choice(controllers(catalogue, entity.id))]
        ultimate = _Planned(
            controller,
            CONTROLLER_PLACEMENTS[placement],
            free.pop() if file_level else transaction,
            stream=f"hits/named/{index + 1}/controller",
            origin="named",
            pair=len(planned),
        )
        planned.extend([replace(plan, pair=len(planned) + 1), ultimate])
    return planned


def _prefer_generated(
    request: EffectiveRequest, placements: list[Placement], free: list[int], exposable: set[int], rng: random.Random
) -> Iterator[int]:
    """A `free` transaction per Placement, where the Placement's role was not supplied while there is one (spec 5.3),
    leaving `exposure_count` of the `exposable` ones to the Exposures."""
    spare = len(exposable) - request.exposure_count
    for placement in placements:
        room = [n for n in free if spare > 0 or n not in exposable]
        preferred = [n for n in room if _supplied(request, placement, n, None) is None]
        number = rng.choice(preferred or room)
        free.remove(number)
        spare -= number in exposable
        yield number


def _supplied(
    request: EffectiveRequest, placement: Placement, transaction: int | None, element: RemittanceElement | None
) -> Displaced | None:
    """The supplied value at a Placement, if any: what a Hit there displaces."""
    if transaction is None:
        role = getattr(request.payment, placement, MISSING) if request.payment else MISSING
        path = f"payment.{placement}"
    elif transaction > len(request.transactions):
        return None
    else:
        row = request.transactions[transaction - 1]
        path = f"transactions[{transaction - 1}]"
        if placement.startswith("intermediary_agent_"):
            slot = int(placement[-1]) - 1
            agents = row.intermediary_agents
            path += ".intermediary_agents"
            role = agents  # a supplied list or null decides every slot; an agent in the slot is what is displaced
            if isinstance(agents, list) and slot < len(agents):
                role, path = agents[slot], f"{path}[{slot}]"
        elif placement == "remittance":
            role, path = _supplied_remittance(row.remittance, element, path)
        else:
            role = getattr(row, placement)
            path += f".{placement}"
    if role is MISSING:
        return None
    value = role.model_dump(mode="json") if isinstance(role, BaseModel) else cast("JsonValue", role)
    return Displaced(field=path, value=value)


def _supplied_remittance(
    remittance: SuppliedRemittance | MISSING, element: RemittanceElement | None, path: str
) -> tuple[object, str]:
    """Without an `element` (while drawing), any supplied remittance counts."""
    if remittance is MISSING or element is None:
        return remittance, f"{path}.remittance"
    if element == "ustrd":
        return remittance.unstructured, f"{path}.remittance.unstructured"
    structured = remittance.structured
    field = _REMITTANCE_FIELDS[element]
    value = getattr(structured, field) if isinstance(structured, SuppliedStructuredRemittance) else MISSING
    return value, f"{path}.remittance.structured.{field}"


def _debtor_agent_at_home(
    planned: list[_Planned], entities: list[Entity], rng: random.Random, request: EffectiveRequest
) -> list[_Planned]:
    """A sanctioned Debtor Agent beside a sanctioned Debtor is a Bank in the Debtor's Listing country, when one is
    free, so the Debtor's account stays at home (spec 6.9). Otherwise the placer keeps the Debtor's own account."""
    file_level = {plan.placement: plan for plan in planned if plan.transaction is None}
    debtor, agent = file_level.get("debtor"), file_level.get("debtor_agent")
    if debtor is None or agent is None or agent.origin == "named":
        return planned
    homes = {address.country for address in _addresses(debtor.entity)} or {_home_country(debtor.entity, None, request)}
    if _bank_countries(agent.entity) & homes:
        return planned
    used = {plan.entity.id for plan in planned}
    banks = [e for e in entities if e.id not in used and _bank_countries(e) & homes]
    if not banks:
        return planned
    bank = rng.choice(banks)
    return [replace(plan, entity=bank) if plan is agent else plan for plan in planned]


def _bank_countries(entity: Entity) -> set[str]:
    """Where a Bank can service an account: its BICs' countries, or its Listing addresses' without a BIC."""
    if not isinstance(entity, Bank):
        return set()
    return {bic_country(bic.value) for bic in entity.bics} if entity.bics else set(entity.countries)


def _home_country(entity: Entity, address: CatalogueAddress | None, request: EffectiveRequest) -> str:
    """Where a sanctioned party banks: its Listing address, else its stated countries, else the Debtor's."""
    if address:
        return address.country
    return entity.countries[0] if entity.countries else request.countries[0]


def _wire_order(plan: _Planned) -> tuple[bool, int, str]:
    return plan.transaction is not None, plan.transaction or 0, xpath(plan.placement, plan.transaction)


def _next_entity(
    queue: list[Entity], entities: list[Entity], unused: set[str], rng: random.Random, fits: Callable[[Entity], bool]
) -> Entity:
    """The next Entity in a shuffled queue that `fits`, refilled when it runs out: distinct until exhausted.

    The first fill leaves out the `unused` ids (the named Hits' Entities) and empties the set, so later fills
    hold the whole catalogue.
    """
    for _ in range(2):
        for index, entity in enumerate(queue):
            if fits(entity):
                return queue.pop(index)
        refill = entities.copy()
        rng.shuffle(refill)
        queue.extend(entity for entity in refill if entity.id not in unused)
        unused.clear()
    msg = "the drawn Hits cannot all be placed: the allowlists or named Hits leave one nowhere to go"
    raise HitsInvalid([error("hit_count", msg=msg)])


class _Placer:
    def __init__(self, request: EffectiveRequest, catalogue: Catalogue, data: GeneratedData) -> None:
        self.request = request
        self.catalogue = catalogue
        self.data = data

    def place(self, model: SampleFileModel) -> tuple[SampleFileModel, list[Hit]]:
        hits: list[Hit] = []
        transactions = list(model.transactions)
        planned = draw(self.request, self.catalogue)
        # Ids follow the Answer Key order (spec 11.4): file-level first, then by transaction number, then by XPath.
        wire_order = sorted(range(len(planned)), key=lambda k: _wire_order(planned[k]))
        ids = {k: f"h{n}" for n, k in enumerate(wire_order, start=1)}
        # The agent's account wins over its Debtor's: the account is serviced by the Bank.
        order = sorted(range(len(planned)), key=lambda k: PLACEMENTS[planned[k].placement].agent)
        debtor_country: str | None = None  # set by a Debtor Hit, which the agents follow
        for k in order:
            plan = planned[k]
            rng = stream(self.request.seed, plan.stream)
            paired_with = ids[plan.pair] if plan.pair is not None else None
            allowed = self.request.name_variants if plan.origin == "drawn" else None
            if plan.placement == "remittance" and plan.transaction is not None:  # always transaction-level
                name = _name(rng, plan.entity, plan.name_variant, allowed)
                element, text = _mention(rng, name.rendered)
                tx = transactions[plan.transaction - 1]
                field = _REMITTANCE_FIELDS[element]
                remittance = replace(tx.remittance, **{field: (text,) if field in _REMITTANCE_LISTS else text})
                transactions[plan.transaction - 1] = replace(tx, remittance=remittance)
                hits.append(self._hit(ids[k], plan, tx.end_to_end_id, name, paired_with, element=element))
                continue
            agent_hit = PLACEMENTS[plan.placement].agent
            bic_only = plan.rendering_mode == "bic_only"
            name = None if bic_only else _name(rng, plan.entity, plan.name_variant, allowed)
            home = debtor_country if plan.placement == "debtor_agent" else None
            bic = None
            if agent_hit and isinstance(plan.entity, Bank) and plan.entity.bics:
                bic = rng.choice([b for b in plan.entity.bics if bic_country(b.value) == home] or plan.entity.bics)
            address = None if bic_only else _address(rng, plan.entity, bic_country(bic.value) if bic else home)
            listed = _listed(address) if address else None
            lei = self._lei(plan.entity) if agent_hit and not bic_only else None
            rendering_mode: RenderingMode | None = None
            local_agent: Agent | None = None  # a sanctioned party's synthetic agent in an Exposure country
            if agent_hit:
                rendering_mode = plan.rendering_mode or ("name_and_bic" if bic else "name_only")
                country = bic_country(bic.value) if bic else _home_country(plan.entity, address, self.request)
                if home is None or country == home:
                    account = self.data.account(rng, country, _bank_code(bic.value) if bic else None)
                else:  # beside a sanctioned Debtor elsewhere, the Debtor's account stands (spec 6.9)
                    account = model.debtor_account
                if rendering_mode == "name_only":  # the BIC still decides the account's country, but is not sent
                    bic = None
                party_or_agent: Party | Agent = Agent(
                    bic=bic.value if bic else None, name=name.rendered if name else None, lei=lei, address=listed
                )
            else:
                assert name is not None  # noqa: S101 - only an agent can be bic_only
                party_or_agent = Party(name=name.rendered, address=listed)
                country = _home_country(plan.entity, address, self.request)
                if country in EXPOSURE_COUNTRIES and plan.placement in {"creditor", "debtor"}:
                    # No clean bank exists there, so a synthetic local one services the account (spec 6.9, 8.3).
                    agent_stream = stream(self.request.seed, f"{plan.stream}/agent")
                    local_agent, account = self.data.exposed_agent_and_account(agent_stream, country)
                else:
                    local_agent, account = None, self.data.account(rng, country, None)
                if plan.placement == "debtor":
                    debtor_country = country
            if plan.transaction is None:
                model = _place_file(model, plan.placement, party_or_agent, account)
                if local_agent:  # a Debtor Agent Hit, placed later, replaces it
                    model = replace(model, debtor_agent=local_agent)
                end_to_end_id = None
            else:
                tx = transactions[plan.transaction - 1]
                placed = self._place_tx(tx, rng, plan.placement, party_or_agent, account)
                transactions[plan.transaction - 1] = (
                    replace(placed, creditor_agent=local_agent) if local_agent else placed
                )
                end_to_end_id = tx.end_to_end_id
            hits.append(
                self._hit(
                    ids[k],
                    plan,
                    end_to_end_id,
                    name,
                    paired_with,
                    rendering_mode=rendering_mode,
                    bic=bic,
                    lei=lei,
                    address=address,
                    version=_version_number(self.request.message_version),
                )
            )
        model = replace(model, transactions=tuple(transactions))
        return model, sorted(hits, key=lambda hit: int(hit.id[1:]))

    def _hit(
        self,
        hit_id: str,
        plan: _Planned,
        end_to_end_id: str | None,
        name: HitName | None,
        paired_with: str | None,
        *,
        element: RemittanceElement | None = None,
        rendering_mode: RenderingMode | None = None,
        bic: Bic | None = None,
        lei: str | None = None,
        address: CatalogueAddress | None = None,
        version: int = 0,
    ) -> Hit:
        leaf = None
        if name is None:  # bic_only: the Hit is the BIC, renamed from .04 on
            leaf = "BIC" if version < _FIRST_WITH_BICFI else "BICFI"
        return Hit(
            id=hit_id,
            scope="file" if plan.transaction is None else "transaction",
            transaction_number=plan.transaction,
            end_to_end_id=end_to_end_id,
            xpath=xpath(plan.placement, plan.transaction, element, leaf),
            entity=HitEntity(
                id=plan.entity.id,
                entity_type=plan.entity.entity_type,
                listings=[listing.ref for listing in plan.entity.listings],
            ),
            placement=plan.placement,
            element=element,
            rendering_mode=rendering_mode,
            name=name,
            bic=HitBic(value=bic.value, source="listing" if bic.listing else "gleif") if bic else None,
            lei=lei,
            address_from_listing=address.listing.entry_id if address else None,
            triggers=_triggers(plan.entity, name.rendered if name else None, bic, lei),
            origin=plan.origin,
            paired_with=paired_with,
            displaced=_supplied(self.request, plan.placement, plan.transaction, element),
        )

    def _lei(self, entity: Entity) -> str | None:
        if isinstance(entity, Individual) or entity.lei is None:
            return None
        return entity.lei.value if _version_number(self.request.message_version) >= _FIRST_WITH_AGENT_LEI else None

    def _place_tx(
        self, tx: Transaction, rng: random.Random, placement: Placement, hit: Party | Agent, account: Account
    ) -> Transaction:
        match placement:
            case "creditor":
                return replace(tx, creditor=hit, creditor_account=account)
            case "creditor_agent":
                return replace(tx, creditor_agent=hit, creditor_account=account)
            case "ultimate_debtor":
                return replace(tx, ultimate_debtor=hit)
            case "ultimate_creditor":
                return replace(tx, ultimate_creditor=hit)
        slot = int(placement[-1])
        agents = list(tx.intermediary_agents)
        while len(agents) < slot - 1:  # contiguous from 1: clean generated banks below the Hit (spec 6.2)
            agents.append(self.data.clean_agent(rng, rng.choice(self.request.countries))[0])
        # A named Hit already in a higher slot keeps it.
        return replace(tx, intermediary_agents=(*agents[: slot - 1], hit, *agents[slot:]))


def place_hits(
    model: SampleFileModel,
    request: EffectiveRequest,
    catalogue: Catalogue,
    data: GeneratedData,
) -> tuple[SampleFileModel, list[Hit]]:
    """Overlay the named and drawn Hits on the clean model; the Hits come back ordered and numbered. Raises
    `HitsInvalid` for a request the catalogue cannot satisfy."""
    return _Placer(request, catalogue, data).place(model)


def _place_file(model: SampleFileModel, placement: Placement, hit: Party | Agent, account: Account) -> SampleFileModel:
    if placement == "debtor":
        return replace(model, debtor=hit, debtor_account=account)
    return replace(model, debtor_agent=hit, debtor_account=account)


def xpath(
    placement: Placement, transaction: int | None, element: RemittanceElement | None = None, leaf: str | None = None
) -> str:
    """Built from the model: lxml's own paths are `/*/*/*[2]` under a default namespace. `leaf` replaces `Nm`."""
    path = REMITTANCE_ELEMENTS[element][0] if element else PLACEMENTS[placement].name_path
    if leaf:
        path = path.removesuffix("Nm") + leaf
    if transaction is None:
        return f"{_PMT_INF}/{path}"
    return f"{_PMT_INF}/CdtTrfTxInf[{transaction}]/{path}"


def _mention(rng: random.Random, name: str) -> tuple[RemittanceElement, str]:
    """The remittance element and its text: the bare name in an invoicer or invoicee `Nm`, else a sentence."""
    elements = {element: weight for element, (_, weight) in REMITTANCE_ELEMENTS.items()}
    (element,) = rng.choices(list(elements), weights=list(elements.values()))
    if element in {"invcr", "invcee"}:
        return element, name
    number = digits(rng, 6)
    # Drawing over the sentences that fit is the spec's redraw of one over 140, without the loop.
    sentences = [s.format(n=number, name=name) for s in REMITTANCE_SENTENCES]
    fitting = [sentence for sentence in sentences if len(sentence) <= _MAX_TEXT]
    if not fitting:  # a name too long for any sentence (over 125 characters) goes bare to an invoice party
        return rng.choice(["invcr", "invcee"]), name
    return element, rng.choice(fitting)


def _name(
    rng: random.Random, entity: Entity, pinned: NameVariant | None = None, allowed: list[NameVariant] | None = None
) -> HitName:
    """A `pinned` variant was checked supported; otherwise one is drawn from those supported and `allowed`."""
    offered = transliterations(entity)
    variant = pinned
    if variant is None:
        supported = supported_name_variants(entity, offered)  # never a name over 140 characters (spec 7.6)
        weights = {v: w for v, w in NAME_VARIANT_WEIGHTS.items() if v in supported and (not allowed or v in allowed)}
        (variant,) = rng.choices(list(weights), weights=list(weights.values()))
    if variant == "transliteration":  # a Cyrillic name, then a scheme that does not collide (spec 7.4)
        name = rng.choice(list(dict.fromkeys(t.name for t in offered)))
        chosen = rng.choice([t for t in offered if t.name == name])
        return HitName(variant=variant, rendered=chosen.latin, source=_source(name), scheme=chosen.scheme)
    if variant == "fuzzed":
        fuzzed = fuzz(rng, entity)
        return HitName(
            variant=variant,
            rendered=fuzzed.rendered,
            source=_source(fuzzed.base),
            base=fuzzed.base.value,
            operations=list(fuzzed.operations),
        )
    pool = [n for n in candidate_names(entity) if VERBATIM_SOURCES[variant](n)]
    if variant == "exact":  # a Listing first, then one of its primary names (spec 7.1)
        listing = rng.choice(list(dict.fromkeys(name.listing for name in pool)))
        pool = [name for name in pool if name.listing == listing]
    name = rng.choice(pool)
    return HitName(variant=variant, rendered=name.value, source=_source(name))


def _source(name: Name) -> NameSource:
    return NameSource(value=name.value, type=name.source_type, script=name.script, listing=name.listing)


def _address(rng: random.Random, entity: Entity, country: str | None) -> CatalogueAddress | None:
    """A Listing address, in `country` when the Listing has one there: an agent's BIC country, else its Debtor's."""
    addresses = _addresses(entity)
    pool = [a for a in addresses if a.country == country] or addresses
    return rng.choice(pool) if pool else None


def _addresses(entity: Entity) -> list[CatalogueAddress]:
    return [] if isinstance(entity, Individual) else entity.addresses


def _listed(address: CatalogueAddress) -> ListedAddress:
    town = " ".join(part for part in (address.postal_code, address.city, address.region) if part)
    return ListedAddress(lines=(*address.lines, *([town] if town else [])), country=address.country)


def _bank_code(bic: str) -> str | None:
    """The Bank's own domestic code where schwifty's registry has it (spec 6.9); BY IBANs carry the BIC's first four."""
    if bic_country(bic) == "BY":
        return bic[:4]
    codes = BIC(bic).domestic_bank_codes
    return codes[0] if codes else None


def _version_number(message_version: str) -> int:
    return int(message_version.rsplit(".", 1)[1])


def _triggers(entity: Entity, rendered: str | None, bic: Bic | None, lei: str | None) -> list[Trigger]:
    """A GLEIF-sourced BIC is on no list, and the UK list has no BIC field (spec 11.3)."""
    triggers = []
    if rendered is not None:
        listed_on = sorted({n.listing.list for n in entity.names if n.value.casefold() == rendered.casefold()})
        triggers.append(Trigger(kind="name", value=rendered, listed_on=listed_on))
    if bic is not None:
        triggers.append(Trigger(kind="bic", value=bic.value, listed_on=[bic.listing.list] if bic.listing else []))
    if lei is not None:
        triggers.append(Trigger(kind="lei", value=lei, listed_on=[]))  # no Listing carries an LEI
    return triggers


def summary_counts(hits: list[Hit], catalogue: Catalogue) -> dict[str, dict[str, int]]:
    """`summary.by_*` (spec 11.2); a Hit counts once per list its Entity is on."""
    lists = Counter(lst for hit in hits for lst in catalogue.entities[hit.entity.id].lists)
    return {
        "by_placement": _sorted(Counter(hit.placement for hit in hits)),
        "by_name_variant": _sorted(Counter(hit.name.variant for hit in hits if hit.name)),
        "by_entity_type": _sorted(Counter(hit.entity.entity_type for hit in hits)),
        "by_list": _sorted(lists),
    }


def _sorted[K: str](counts: Counter[K]) -> dict[str, int]:
    return dict(sorted(counts.items()))
