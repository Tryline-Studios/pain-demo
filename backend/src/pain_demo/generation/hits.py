"""Drawn Hits (spec 6, 7): Sanctioned Entities placed into a clean Sample File model, and the Answer Key entries
that say where each one is (spec 11.3, 11.4).

The clean model is drawn first and Hits are overlaid from their own streams (`hits/placement`, then `hits/<k>` per
Hit), so Hit Count 0 leaves the file untouched and adding a Hit never reshuffles an innocent row (spec 9.3).
"""

import random
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

from pydantic import BaseModel, Field
from schwifty import BIC

from pain_demo.catalogue import Catalogue
from pain_demo.catalogue.capabilities import (
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
from pain_demo.generation.request import EffectiveRequest
from pain_demo.generation.seeds import stream
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
    rendering_mode: Literal["name_and_bic", "bic_only", "name_only"] | None = Field(
        default=None, exclude_if=_absent, description="Agents only"
    )
    name: HitName | None
    bic: HitBic | None
    lei: str | None
    address_from_listing: str | None
    """The `entry_id` of the Listing whose address the Placement carries."""
    triggers: list[Trigger]
    origin: Literal["named", "drawn"]
    paired_with: str | None
    """Always null until named Hits with `with_controller` pair them."""
    displaced: None
    """Always null until Supplied Data can be displaced by a Hit."""


@dataclass(frozen=True)
class _Planned:
    entity: Entity
    placement: Placement
    transaction: int | None = None


def draw(request: EffectiveRequest, catalogue: Catalogue) -> list[_Planned]:
    """Entities, Placements and transaction numbers, all from the placement stream (spec 6.3, 6.5).

    Every valid Hit Count succeeds: once the Hits left outnumber the free transactions, the Hit must go to a free
    file-level Placement, and a Hit that can only take the Debtor Agent goes to the next Bank in the queue.
    """
    rng = stream(request.seed, "hits/placement")
    entities = list(catalogue.entities.values())
    queue: list[Entity] = []
    taken: set[Placement] = set()
    free_transactions = request.transaction_count
    planned: list[_Planned] = []
    for drawn in range(request.hit_count):
        forced = request.hit_count - drawn > free_transactions

        def weights(entity: Entity, *, forced: bool = forced) -> dict[Placement, float]:
            # Leaving taken file-level Placements out is the spec's "redrawn", without the loop.
            table = placement_weights(entity.entity_type)
            return {p: w for p, w in table.items() if p not in taken and (PLACEMENTS[p].file_level or not forced)}

        entity = _next_entity(queue, entities, rng, lambda entity: bool(weights(entity)))
        options = weights(entity)
        (placement,) = rng.choices(list(options), weights=list(options.values()))
        if PLACEMENTS[placement].file_level:
            taken.add(placement)
        else:
            free_transactions -= 1
        planned.append(_Planned(entity, placement))
    numbers = iter(rng.sample(range(1, request.transaction_count + 1), request.transaction_count - free_transactions))
    planned = [p if PLACEMENTS[p.placement].file_level else replace(p, transaction=next(numbers)) for p in planned]
    return _debtor_agent_at_home(planned, entities, rng, request)


def _debtor_agent_at_home(
    planned: list[_Planned], entities: list[Entity], rng: random.Random, request: EffectiveRequest
) -> list[_Planned]:
    """A sanctioned Debtor Agent beside a sanctioned Debtor is a Bank in the Debtor's Listing country, when one is
    free, so the Debtor's account stays at home (spec 6.9). Otherwise the placer keeps the Debtor's own account."""
    file_level = {plan.placement: plan for plan in planned if plan.transaction is None}
    debtor, agent = file_level.get("debtor"), file_level.get("debtor_agent")
    if debtor is None or agent is None:
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
    queue: list[Entity], entities: list[Entity], rng: random.Random, fits: Callable[[Entity], bool]
) -> Entity:
    """The next Entity in a shuffled queue that `fits`, refilled when it runs out: distinct until exhausted."""
    for _ in range(2):
        for index, entity in enumerate(queue):
            if fits(entity):
                return queue.pop(index)
        refill = entities.copy()
        rng.shuffle(refill)
        queue.extend(refill)
    msg = "the catalogue has no Bank for the Debtor Agent Hit"
    raise RuntimeError(msg)


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
            rng = stream(self.request.seed, f"hits/{k + 1}")
            name = _name(rng, plan.entity)
            if plan.placement == "remittance" and plan.transaction is not None:  # always transaction-level
                element, text = _mention(rng, name.rendered)
                tx = transactions[plan.transaction - 1]
                remittance = replace(tx.remittance, **{_REMITTANCE_FIELDS[element]: text})
                transactions[plan.transaction - 1] = replace(tx, remittance=remittance)
                hits.append(self._hit(ids[k], plan, tx.end_to_end_id, name, element=element))
                continue
            agent_hit = PLACEMENTS[plan.placement].agent
            home = debtor_country if plan.placement == "debtor_agent" else None
            bic = None
            if agent_hit and isinstance(plan.entity, Bank) and plan.entity.bics:
                bic = rng.choice([b for b in plan.entity.bics if bic_country(b.value) == home] or plan.entity.bics)
            address = _address(rng, plan.entity, bic_country(bic.value) if bic else home)
            listed = _listed(address) if address else None
            lei = self._lei(plan.entity) if agent_hit else None
            if agent_hit:
                party_or_agent: Party | Agent = Agent(
                    bic=bic.value if bic else None, name=name.rendered, lei=lei, address=listed
                )
                country = bic_country(bic.value) if bic else _home_country(plan.entity, address, self.request)
                if home is None or country == home:
                    account = self.data.account(rng, country, _bank_code(bic.value) if bic else None)
                else:  # beside a sanctioned Debtor elsewhere, the Debtor's account stands (spec 6.9)
                    account = model.debtor_account
            else:
                party_or_agent = Party(name=name.rendered, address=listed)
                country = _home_country(plan.entity, address, self.request)
                account = self.data.account(rng, country, None)
                if plan.placement == "debtor":
                    debtor_country = country
            if plan.transaction is None:
                model = _place_file(model, plan.placement, party_or_agent, account)
                end_to_end_id = None
            else:
                tx = transactions[plan.transaction - 1]
                transactions[plan.transaction - 1] = self._place_tx(tx, rng, plan.placement, party_or_agent, account)
                end_to_end_id = tx.end_to_end_id
            hits.append(
                self._hit(
                    ids[k],
                    plan,
                    end_to_end_id,
                    name,
                    rendering_mode=("name_and_bic" if bic else "name_only") if agent_hit else None,
                    bic=bic,
                    lei=lei,
                    address=address,
                )
            )
        model = replace(model, transactions=tuple(transactions))
        return model, sorted(hits, key=lambda hit: int(hit.id[1:]))

    @staticmethod
    def _hit(
        hit_id: str,
        plan: _Planned,
        end_to_end_id: str | None,
        name: HitName,
        *,
        element: RemittanceElement | None = None,
        rendering_mode: Literal["name_and_bic", "name_only"] | None = None,
        bic: Bic | None = None,
        lei: str | None = None,
        address: CatalogueAddress | None = None,
    ) -> Hit:
        return Hit(
            id=hit_id,
            scope="file" if plan.transaction is None else "transaction",
            transaction_number=plan.transaction,
            end_to_end_id=end_to_end_id,
            xpath=xpath(plan.placement, plan.transaction, element),
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
            triggers=_triggers(plan.entity, name.rendered, bic, lei),
            origin="drawn",
            paired_with=None,
            displaced=None,
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
        agents = list(tx.intermediary_agents[: slot - 1])
        while len(agents) < slot - 1:  # contiguous from 1: clean generated banks below the Hit (spec 6.2)
            agents.append(self.data.clean_agent(rng, rng.choice(self.request.countries))[0])
        return replace(tx, intermediary_agents=(*agents, hit))


def place_hits(
    model: SampleFileModel,
    request: EffectiveRequest,
    catalogue: Catalogue,
    data: GeneratedData,
) -> tuple[SampleFileModel, list[Hit]]:
    """Overlay `request.hit_count` drawn Hits on the clean model; the Hits come back ordered and numbered."""
    return _Placer(request, catalogue, data).place(model)


def _place_file(model: SampleFileModel, placement: Placement, hit: Party | Agent, account: Account) -> SampleFileModel:
    if placement == "debtor":
        return replace(model, debtor=hit, debtor_account=account)
    return replace(model, debtor_agent=hit, debtor_account=account)


def xpath(placement: Placement, transaction: int | None, element: RemittanceElement | None = None) -> str:
    """Built from the model: lxml's own paths are `/*/*/*[2]` under a default namespace."""
    path = REMITTANCE_ELEMENTS[element][0] if element else PLACEMENTS[placement].name_path
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


def _name(rng: random.Random, entity: Entity) -> HitName:
    offered = transliterations(entity)
    supported = supported_name_variants(entity, offered)  # never a name over 140 characters (spec 7.6)
    weights = {variant: w for variant, w in NAME_VARIANT_WEIGHTS.items() if variant in supported}
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


def _triggers(entity: Entity, rendered: str, bic: Bic | None, lei: str | None) -> list[Trigger]:
    listed_on = sorted({n.listing.list for n in entity.names if n.value.casefold() == rendered.casefold()})
    triggers = [Trigger(kind="name", value=rendered, listed_on=listed_on)]
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
