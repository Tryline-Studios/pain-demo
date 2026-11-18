"""What an Entity supports: Name Variants (spec 7.6) and Placements (spec 6.1), as `GET /entities` publishes them."""

from collections.abc import Callable
from typing import Literal, NamedTuple

from pain_workbench.catalogue.schema import Entity, EntityType, Name
from pain_workbench.catalogue.transliteration import SCHEMES, TransliterationScheme, transliterate

type NameVariant = Literal["exact", "alias", "native_script", "transliteration", "fuzzed"]
type Placement = Literal[
    "debtor",
    "debtor_agent",
    "creditor",
    "creditor_agent",
    "ultimate_debtor",
    "ultimate_creditor",
    "intermediary_agent_1",
    "intermediary_agent_2",
    "intermediary_agent_3",
    "remittance",
]

MAX_NAME_LENGTH = 140
"""`Nm` is `Max140Text`: longer names are never candidates for any variant."""

LEGAL_ENTITIES: frozenset[EntityType] = frozenset({"bank", "corporate"})
EVERY_TYPE: frozenset[EntityType] = frozenset({"individual", *LEGAL_ENTITIES})
BANK_ONLY: frozenset[EntityType] = frozenset({"bank"})

PLACEMENT_ELIGIBILITY: dict[Placement, frozenset[EntityType]] = {
    "debtor": EVERY_TYPE,
    "debtor_agent": BANK_ONLY,
    "creditor": EVERY_TYPE,
    "creditor_agent": BANK_ONLY,
    "ultimate_debtor": EVERY_TYPE,
    "ultimate_creditor": EVERY_TYPE,
    "intermediary_agent_1": BANK_ONLY,
    "intermediary_agent_2": BANK_ONLY,
    "intermediary_agent_3": BANK_ONLY,
    "remittance": EVERY_TYPE,
}
"""The spec 6.1 table, in Placement enum order."""
FILE_LEVEL_PLACEMENTS: frozenset[Placement] = frozenset({"debtor", "debtor_agent"})
"""One `PmtInf` per Sample File: at most one Entity in each (spec 6.2)."""
AGENT_PLACEMENTS: frozenset[Placement] = frozenset(
    p for p, types in PLACEMENT_ELIGIBILITY.items() if types == BANK_ONLY
)
CONTROLLER_PLACEMENTS: dict[Placement, Placement] = {"creditor": "ultimate_creditor", "debtor": "ultimate_debtor"}
"""Where a controlled Legal Entity may stand with `with_controller`, and where its controller then goes (spec 6.8)."""


def candidate_names(entity: Entity) -> list[Name]:
    return [name for name in entity.names if len(name.value) <= MAX_NAME_LENGTH]


VERBATIM_SOURCES: dict[NameVariant, Callable[[Name], bool]] = {
    # A non-Latin primary name (ПАО Сбербанк) is a native_script source, not an exact one.
    "exact": lambda name: name.source_type == "primary" and name.script == "latin",
    "alias": lambda name: name.source_type != "primary" and name.script == "latin",
    "native_script": lambda name: name.script != "latin",
}
"""Which catalogue names each verbatim Name Variant renders (spec 7.1 to 7.3)."""


class Transliteration(NamedTuple):
    name: Name
    """The listed Cyrillic name."""
    scheme: TransliterationScheme
    latin: str


def transliterations(entity: Entity) -> list[Transliteration]:
    """Every transliteration that fits `Nm` and is no listed Latin name, case-insensitively (spec 7.4); a colliding
    scheme is simply not among them."""
    listed = {name.value.casefold() for name in entity.names if name.script == "latin"}
    found = []
    for name in candidate_names(entity):
        if name.script == "cyrillic":
            for scheme in SCHEMES:
                latin = transliterate(name.value, scheme)
                if latin.casefold() not in listed and len(latin) <= MAX_NAME_LENGTH:
                    found.append(Transliteration(name, scheme, latin))
    return found


def supported_name_variants(entity: Entity, offered: list[Transliteration] | None = None) -> list[NameVariant]:
    """`offered` is `transliterations(entity)` when the caller already has it."""
    names = candidate_names(entity)
    variants: list[NameVariant] = ["exact"]
    if any(map(VERBATIM_SOURCES["alias"], names)):
        variants.append("alias")
    if any(map(VERBATIM_SOURCES["native_script"], names)):
        variants.append("native_script")
    if offered if offered is not None else transliterations(entity):
        variants.append("transliteration")
    if any(name.script == "latin" for name in names):  # a fuzz needs a Latin base (spec 7.5)
        variants.append("fuzzed")
    return variants


def supported_placements(entity_type: EntityType) -> list[Placement]:
    return [placement for placement, eligible in PLACEMENT_ELIGIBILITY.items() if entity_type in eligible]
