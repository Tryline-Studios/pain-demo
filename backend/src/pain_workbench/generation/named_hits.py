"""Named Hits checked against the catalogue (spec 6.4, 6.6, 6.8, 7.6): every impossible combination is a 422 naming
the Entity and the field."""

from typing import Any

from pain_workbench.catalogue import Catalogue
from pain_workbench.catalogue.capabilities import (
    AGENT_PLACEMENTS,
    CONTROLLER_PLACEMENTS,
    FILE_LEVEL_PLACEMENTS,
    PLACEMENT_ELIGIBILITY,
    Placement,
    supported_name_variants,
    supported_placements,
)
from pain_workbench.catalogue.schema import Bank, Entity
from pain_workbench.generation.request import EffectiveRequest, NamedHit


class HitsInvalid(Exception):
    """Errors in Pydantic's shape (`loc`, `msg`, `type`), so the problem handlers render them like any 422."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__("; ".join(error["msg"] for error in errors))
        self.errors = errors


def error(*loc: str | int, msg: str) -> dict[str, Any]:
    return {"loc": ("body", *loc), "msg": msg, "type": "value_error"}


def placement_options(hit: NamedHit, entity: Entity) -> list[Placement]:
    """The Placements a named Hit may take given everything else it pins, in enum order."""
    options = [hit.placement] if hit.placement else supported_placements(entity.entity_type)
    return [
        p
        for p in options
        if (hit.rendering_mode is None or p in AGENT_PLACEMENTS)
        and (not hit.with_controller or p in CONTROLLER_PLACEMENTS)
        and (hit.transaction is None or p not in FILE_LEVEL_PLACEMENTS)
    ]


def controllers(catalogue: Catalogue, entity_id: str) -> list[str]:
    return sorted({r.controller for r in catalogue.relationships if r.controlled == entity_id})


def check(request: EffectiveRequest, catalogue: Catalogue) -> None:
    errors: list[dict[str, Any]] = []
    named = sum(hit.weight for hit in request.hits)
    if named > request.hit_count:
        errors.append(error("hits", msg=f"{named} named Hits (with_controller counts two) exceed hit_count"))
    for index, hit in enumerate(request.hits):
        errors.extend(_hit_errors(index, hit, request, catalogue))
    if not errors:
        errors.extend(_clashes(request))
    if errors:
        raise HitsInvalid(errors)


def _hit_errors(index: int, hit: NamedHit, request: EffectiveRequest, catalogue: Catalogue) -> list[dict[str, Any]]:
    entity = catalogue.entities.get(hit.entity)
    if entity is None:
        return [error("hits", index, "entity", msg=f"{hit.entity!r} is not in the Entity Catalogue")]
    name, kind = entity.id, entity.entity_type
    errors = []

    def fail(field: str, message: str) -> None:
        errors.append(error("hits", index, field, msg=f"{name}: {message}"))

    if hit.placement and kind not in PLACEMENT_ELIGIBILITY[hit.placement]:
        fail("placement", f"a {kind} cannot be placed as {hit.placement}")
    if hit.name_variant and hit.rendering_mode == "bic_only":
        fail("name_variant", "bic_only renders no name, so it takes no Name Variant")
    elif hit.name_variant and hit.name_variant not in supported_name_variants(entity):
        fail("name_variant", f"does not support the {hit.name_variant} Name Variant")
    if hit.transaction is not None:
        if hit.placement in FILE_LEVEL_PLACEMENTS:
            fail("transaction", f"must be absent for the file-level Placement {hit.placement}")
        elif hit.transaction > request.transaction_count:
            fail("transaction", f"transaction {hit.transaction} is outside 1 to {request.transaction_count}")
    if hit.rendering_mode:
        if not isinstance(entity, Bank):
            fail("rendering_mode", f"rendering modes are for agents, and a {kind} is never one")
        elif hit.placement and hit.placement not in AGENT_PLACEMENTS:
            fail("rendering_mode", f"rendering modes are for agents, not {hit.placement}")
        elif hit.with_controller:
            fail("rendering_mode", "with_controller places a party, not an agent")
        elif hit.rendering_mode == "bic_only" and not entity.bics:
            fail("rendering_mode", "has no catalogue BIC, so it cannot be bic_only")
    if hit.with_controller:
        if not controllers(catalogue, entity.id):
            fail("with_controller", "has no controller in the Entity Catalogue")
        elif hit.placement and hit.placement not in CONTROLLER_PLACEMENTS:
            fail("with_controller", f"a controller pairs with a creditor or debtor, not {hit.placement}")
    if not errors and not placement_options(hit, entity):
        fail("placement", "no Placement fits what this Hit pins")
    return errors


def _clashes(request: EffectiveRequest) -> list[dict[str, Any]]:
    """Two pinned named Hits on the same slot: the same file-level Placement, or the same Placement in the same
    transaction (a controller's Ultimate party included)."""
    errors = []
    slots: dict[tuple[Placement, int | None], int] = {}
    for index, hit in enumerate(request.hits):
        if hit.placement is None or (hit.transaction is None and hit.placement not in FILE_LEVEL_PLACEMENTS):
            continue
        wanted = [(hit.placement, hit.transaction)]
        if hit.with_controller and hit.transaction is not None:
            wanted.append((CONTROLLER_PLACEMENTS[hit.placement], hit.transaction))
        for slot in wanted:
            if slot in slots:
                other = request.hits[slots[slot]].entity
                where = "the file" if slot[1] is None else f"transaction {slot[1]}"
                errors.append(
                    error("hits", index, "placement", msg=f"{hit.entity}: {other} is already {slot[0]} in {where}")
                )
            slots[slot] = index
    return errors
