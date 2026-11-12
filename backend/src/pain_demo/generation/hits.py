"""Drawn Hits (spec 6, 7): Sanctioned Entities placed into a clean Sample File model, and the Answer Key entries
that say where each one is (spec 11.3, 11.4).

The clean model is drawn first and Hits are overlaid from their own streams (`hits/placement`, then `hits/<k>` per
Hit), so Hit Count 0 leaves the file untouched and adding a Hit never reshuffles an innocent row (spec 9.3).
"""

import random
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal, cast

from pydantic import BaseModel, Field
from schwifty import BIC, IBAN

from pain_demo.catalogue import Catalogue
from pain_demo.catalogue.capabilities import NameVariant, Placement, candidate_names
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
from pain_demo.generation.clean_banks import IBAN_COUNTRIES, CleanBankList, SupportedCountry
from pain_demo.generation.generated_data import COUNTRIES, GeneratedData, digits
from pain_demo.generation.model import (
    Account,
    Agent,
    Iban,
    ListedAddress,
    OtherAccount,
    Party,
    SampleFileModel,
    Transaction,
)
from pain_demo.generation.request import EffectiveRequest
from pain_demo.generation.seeds import stream

PARTY_WEIGHTS: dict[Placement, float] = {"creditor": 35, "ultimate_creditor": 15, "ultimate_debtor": 15, "debtor": 10}
"""Placement of a Corporate or Individual (spec 6.5). The remittance mention (25) joins with its own ticket."""
_SLOT_WEIGHTS: dict[Placement, float] = {
    "intermediary_agent_1": 60,
    "intermediary_agent_2": 30,
    "intermediary_agent_3": 10,
}
_BANK_PARTY_ROLES = 10
"""A Bank's "party roles 10", which the spec does not split: shared over the party roles as `PARTY_WEIGHTS` are."""
BANK_WEIGHTS: dict[Placement, float] = {
    "creditor_agent": 40,
    **{slot: 30 * weight / 100 for slot, weight in _SLOT_WEIGHTS.items()},
    "debtor_agent": 15,
    **{role: _BANK_PARTY_ROLES * weight / sum(PARTY_WEIGHTS.values()) for role, weight in PARTY_WEIGHTS.items()},
}
"""Placement of a Bank (spec 6.5), the Intermediary Agent's 30 shared by the slot weights 60/30/10. The remittance
mention (5) joins with its own ticket."""
NAME_VARIANT_WEIGHTS: dict[NameVariant, float] = {"exact": 40, "alias": 25, "native_script": 5}
"""The verbatim Name Variants (spec 6.5); transliteration and fuzzed join with their own tickets."""
FILE_LEVEL: tuple[Placement, ...] = ("debtor", "debtor_agent")
AGENTS: frozenset[Placement] = frozenset(
    {"debtor_agent", "creditor_agent", "intermediary_agent_1", "intermediary_agent_2", "intermediary_agent_3"}
)
_IBAN_COUNTRIES = frozenset({"BY", "IR", *IBAN_COUNTRIES})
"""Where a Hit's account is an IBAN (spec 6.9); everywhere else it is `Othr/Id`."""
_PMT_INF = "/Document/CstmrCdtTrfInitn/PmtInf"
_NAME_PATHS: dict[Placement, str] = {
    "debtor": "Dbtr/Nm",
    "debtor_agent": "DbtrAgt/FinInstnId/Nm",
    "creditor": "Cdtr/Nm",
    "creditor_agent": "CdtrAgt/FinInstnId/Nm",
    "ultimate_debtor": "UltmtDbtr/Nm",
    "ultimate_creditor": "UltmtCdtr/Nm",
    "intermediary_agent_1": "IntrmyAgt1/FinInstnId/Nm",
    "intermediary_agent_2": "IntrmyAgt2/FinInstnId/Nm",
    "intermediary_agent_3": "IntrmyAgt3/FinInstnId/Nm",
}
_FIRST_WITH_AGENT_LEI = "pain.001.001.09"
"""`FinInstnId/LEI` exists from .09; earlier versions get no LEI rather than a dropped one."""


def _exact(name: Name) -> bool:
    # A non-Latin primary name (ПАО Сбербанк) is a native_script candidate, not an exact one.
    return name.source_type == "primary" and name.script == "latin"


_CANDIDATES = {
    "exact": _exact,
    "alias": lambda name: name.source_type != "primary" and name.script == "latin",
    "native_script": lambda name: name.script != "latin",
}


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


def _absent(value: object) -> bool:
    return value is None


class Hit(BaseModel):
    """One Placement of a Sanctioned Entity (spec 11.3), in wire order. `element` (remittance) arrives later."""

    id: str
    scope: Literal["file", "transaction"]
    transaction_number: int | None = Field(default=None, exclude_if=_absent, description="Absent for scope file")
    end_to_end_id: str | None = Field(default=None, exclude_if=_absent, description="Absent for scope file")
    xpath: str
    entity: HitEntity
    placement: Placement
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
            table = BANK_WEIGHTS if entity.entity_type == "bank" else PARTY_WEIGHTS
            return {p: w for p, w in table.items() if p not in taken and (p in FILE_LEVEL or not forced)}

        entity = _next_entity(queue, entities, rng, lambda entity: bool(weights(entity)))
        options = weights(entity)
        (placement,) = rng.choices(list(options), weights=list(options.values()))
        if placement in FILE_LEVEL:
            taken.add(placement)
        else:
            free_transactions -= 1
        planned.append(_Planned(entity, placement))
    numbers = iter(rng.sample(range(1, request.transaction_count + 1), request.transaction_count - free_transactions))
    return [p if p.placement in FILE_LEVEL else replace(p, transaction=next(numbers)) for p in planned]


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
    def __init__(
        self, request: EffectiveRequest, catalogue: Catalogue, clean_banks: CleanBankList, data: GeneratedData
    ) -> None:
        self.request = request
        self.catalogue = catalogue
        self.clean_banks = clean_banks
        self.data = data

    def place(self, model: SampleFileModel) -> tuple[SampleFileModel, list[Hit]]:
        hits: list[Hit] = []
        transactions = list(model.transactions)
        planned = draw(self.request, self.catalogue)
        # The agent's account wins over its Debtor's: the account is serviced by the Bank.
        order = sorted(range(len(planned)), key=lambda k: planned[k].placement in AGENTS)
        for k in order:
            plan = planned[k]
            rng = stream(self.request.seed, f"hits/{k + 1}")
            name = _name(rng, plan.entity)
            agent_hit = plan.placement in AGENTS
            bic = (
                rng.choice(plan.entity.bics)
                if agent_hit and isinstance(plan.entity, Bank) and plan.entity.bics
                else None
            )
            address = _address(rng, plan.entity, bic.value[4:6] if bic else None)
            listed = _listed(address) if address else None
            lei = self._lei(plan.entity) if agent_hit else None
            if agent_hit:
                party_or_agent: Party | Agent = Agent(
                    bic=bic.value if bic else None, name=name.rendered, lei=lei, address=listed
                )
                country = bic.value[4:6] if bic else self._country(plan.entity, address)
                account = self._account(rng, country, _bank_code(bic.value) if bic else None)
            else:
                party_or_agent = Party(name=name.rendered, address=listed)
                account = self._account(rng, self._country(plan.entity, address), None)
            if plan.transaction is None:
                model = _place_file(model, plan.placement, party_or_agent, account)
                end_to_end_id = None
            else:
                tx = transactions[plan.transaction - 1]
                transactions[plan.transaction - 1] = self._place_tx(tx, rng, plan.placement, party_or_agent, account)
                end_to_end_id = tx.end_to_end_id
            hits.append(
                Hit(
                    id="",
                    scope="file" if plan.transaction is None else "transaction",
                    transaction_number=plan.transaction,
                    end_to_end_id=end_to_end_id,
                    xpath=xpath(plan.placement, plan.transaction),
                    entity=HitEntity(
                        id=plan.entity.id,
                        entity_type=plan.entity.entity_type,
                        listings=[listing.ref for listing in plan.entity.listings],
                    ),
                    placement=plan.placement,
                    rendering_mode=("name_and_bic" if bic else "name_only") if agent_hit else None,
                    name=name,
                    bic=HitBic(value=bic.value, source="listing" if bic.listing else "gleif") if bic else None,
                    lei=lei,
                    address_from_listing=address.listing.entry_id if address else None,
                    triggers=_triggers(plan.entity, name.rendered, bic, lei),
                    origin="drawn",
                    paired_with=None,
                    displaced=None,
                )
            )
        model = replace(model, transactions=tuple(transactions))
        hits.sort(key=lambda hit: (hit.scope != "file", hit.transaction_number or 0, hit.xpath))
        return model, [hit.model_copy(update={"id": f"h{n}"}) for n, hit in enumerate(hits, start=1)]

    def _lei(self, entity: Entity) -> str | None:
        if isinstance(entity, Individual) or entity.lei is None:
            return None
        return entity.lei.value if self.request.message_version >= _FIRST_WITH_AGENT_LEI else None

    def _country(self, entity: Entity, address: CatalogueAddress | None) -> str:
        """Where a sanctioned party banks: its Listing address, else its stated countries, else the Debtor's."""
        if address:
            return address.country
        return entity.countries[0] if entity.countries else self.request.countries[0]

    def _account(self, rng: random.Random, country: str, bank_code: str | None) -> Account:
        """A clean account in `country` (spec 6.9): IBAN for BY, IR and the IBAN defaults, else `Othr/Id`."""
        if country == "IR":
            # schwifty's IR spec has no bank or account positions and yields all zeros: BBAN 0 + bank + 18 digits.
            return Iban(_iban("IR", "0" + digits(rng, 21)))
        profile = COUNTRIES.get(country)  # one of the twelve clean countries, else None
        if country in _IBAN_COUNTRIES:
            account_digits = profile.account_digits if profile else 16  # BY: 16 after the bank code and branch
            if bank_code is None and profile:
                bank_code = rng.choice(self.clean_banks.for_country(cast("SupportedCountry", country))).bank_code
            codes = {"bank_code": bank_code} if bank_code else {}
            if account_digits:
                codes["account_code"] = digits(rng, account_digits)
            return Iban(str(IBAN.random(country, random=rng, use_registry=False, **codes)))
        if country == "RU":
            return OtherAccount("40702810" + digits(rng, 12))  # 20 digits: balance account, currency, then the rest
        return OtherAccount(digits(rng, (profile.account_digits or 10) if profile else 16))

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
    clean_banks: CleanBankList,
    data: GeneratedData,
) -> tuple[SampleFileModel, list[Hit]]:
    """Overlay `request.hit_count` drawn Hits on the clean model; the Hits come back ordered and numbered."""
    return _Placer(request, catalogue, clean_banks, data).place(model)


def _place_file(model: SampleFileModel, placement: Placement, hit: Party | Agent, account: Account) -> SampleFileModel:
    if placement == "debtor":
        return replace(model, debtor=hit, debtor_account=account)
    return replace(model, debtor_agent=hit, debtor_account=account)


def xpath(placement: Placement, transaction: int | None) -> str:
    """Built from the model: lxml's own paths are `/*/*/*[2]` under a default namespace."""
    if transaction is None:
        return f"{_PMT_INF}/{_NAME_PATHS[placement]}"
    return f"{_PMT_INF}/CdtTrfTxInf[{transaction}]/{_NAME_PATHS[placement]}"


def _name(rng: random.Random, entity: Entity) -> HitName:
    names = candidate_names(entity)  # never over 140 characters (spec 7.6)
    candidates = {variant: [n for n in names if _CANDIDATES[variant](n)] for variant in NAME_VARIANT_WEIGHTS}
    weights = {variant: w for variant, w in NAME_VARIANT_WEIGHTS.items() if candidates[variant]}
    (variant,) = rng.choices(list(weights), weights=list(weights.values()))
    name = rng.choice(candidates[variant])
    source = NameSource(value=name.value, type=name.source_type, script=name.script, listing=name.listing)
    return HitName(variant=variant, rendered=name.value, source=source)


def _address(rng: random.Random, entity: Entity, bic_country: str | None) -> CatalogueAddress | None:
    """A Listing address; an agent's in its BIC's country when the Listing has one there."""
    addresses = [] if isinstance(entity, Individual) else entity.addresses
    in_bic_country = [a for a in addresses if a.country == bic_country]
    pool = in_bic_country or addresses
    return rng.choice(pool) if pool else None


def _listed(address: CatalogueAddress) -> ListedAddress:
    town = " ".join(part for part in (address.postal_code, address.city, address.region) if part)
    return ListedAddress(lines=(*address.lines, *([town] if town else [])), country=address.country)


def _bank_code(bic: str) -> str | None:
    """The Bank's own domestic code where schwifty's registry has it (spec 6.9); BY IBANs carry the BIC's first four."""
    if bic[4:6] == "BY":
        return bic[:4]
    codes = BIC(bic).domestic_bank_codes
    return codes[0] if codes else None


def _iban(country: str, bban: str) -> str:
    numeric = int("".join(str(int(char, 36)) for char in bban + country + "00"))
    return f"{country}{98 - numeric % 97:02d}{bban}"


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
