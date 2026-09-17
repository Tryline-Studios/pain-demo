"""What an Entity supports: Name Variants (spec 7.6) and Placements (spec 6.1), as `GET /entities` publishes them.

`transliteration` joins the supported set with its own ticket, once the scheme collision check exists.
"""

from typing import Literal

from pain_demo.catalogue.schema import Entity, EntityType, Name

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

PARTY_PLACEMENTS: tuple[Placement, ...] = ("debtor", "creditor", "ultimate_debtor", "ultimate_creditor")
AGENT_PLACEMENTS: tuple[Placement, ...] = (
    "debtor_agent",
    "creditor_agent",
    "intermediary_agent_1",
    "intermediary_agent_2",
    "intermediary_agent_3",
)
PLACEMENT_ORDER: tuple[Placement, ...] = (
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
)


def candidate_names(entity: Entity) -> list[Name]:
    return [name for name in entity.names if len(name.value) <= MAX_NAME_LENGTH]


def supported_name_variants(entity: Entity) -> list[NameVariant]:
    names = candidate_names(entity)
    variants: list[NameVariant] = ["exact"]
    if any(name.script == "latin" and name.source_type != "primary" for name in names):
        variants.append("alias")
    if any(name.script != "latin" for name in names):
        variants.append("native_script")
    variants.append("fuzzed")
    return variants


def supported_placements(entity_type: EntityType) -> list[Placement]:
    allowed = {*PARTY_PLACEMENTS, "remittance", *(AGENT_PLACEMENTS if entity_type == "bank" else ())}
    return [placement for placement in PLACEMENT_ORDER if placement in allowed]
