"""Loads and validates the Entity Catalogue at startup (spec section 3.3).

Every problem in the catalogue is collected before `CatalogueError` is raised, so one failed start lists them all.
"""

import tomllib
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from pain_demo.catalogue.schema import (
    ControlRelationship,
    ControlRelationshipsFile,
    Entity,
    Individual,
)

DEFAULT_ROOT = Path(__file__).parent
ENTITIES_DIR = "entities"
CONTROL_RELATIONSHIPS_FILE = "control_relationships.toml"

_entity_adapter: TypeAdapter[Entity] = TypeAdapter(Entity)


class CatalogueError(Exception):
    """The catalogue on disk is not usable; `problems` lists every reason."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


class Catalogue:
    """The validated Entity Catalogue: Entities by id, in id order, plus their Control Relationships."""

    def __init__(self, entities: list[Entity], relationships: list[ControlRelationship]) -> None:
        self.entities: dict[str, Entity] = {entity.id: entity for entity in sorted(entities, key=lambda e: e.id)}
        self.relationships = relationships

    def get(self, entity_id: str) -> Entity | None:
        return self.entities.get(entity_id)

    def relationships_of(self, entity_id: str) -> list[ControlRelationship]:
        return [r for r in self.relationships if entity_id in (r.controller, r.controlled)]

    @property
    def snapshot_date(self) -> date:
        """The latest list snapshot any Listing was verified against: the Generator Version's `catalogue_snapshot`."""
        return max(listing.verified.snapshot_date for entity in self.entities.values() for listing in entity.listings)


def load_catalogue(root: Path = DEFAULT_ROOT) -> Catalogue:
    problems: list[str] = []
    entities = _load_entities(root / ENTITIES_DIR, problems)
    relationships = _load_relationships(root / CONTROL_RELATIONSHIPS_FILE, problems)
    _check_relationships(entities, relationships, problems)
    if problems:
        raise CatalogueError(problems)
    return Catalogue(entities, relationships)


def _load_entities(entities_dir: Path, problems: list[str]) -> list[Entity]:
    entities: list[Entity] = []
    seen: set[str] = set()
    for path in sorted(entities_dir.glob("*.toml")):
        entity = _parse(path, _entity_adapter.validate_python, problems)
        if entity is None:
            continue
        if entity.id != path.stem:
            problems.append(f"{path.name}: id {entity.id!r} does not match the filename")
        if entity.id in seen:
            problems.append(f"{path.name}: duplicate id {entity.id!r}")
        seen.add(entity.id)
        entities.append(entity)
    if not entities and not problems:
        problems.append(f"{entities_dir}: no Entity files found")
    return entities


def _load_relationships(path: Path, problems: list[str]) -> list[ControlRelationship]:
    if not path.exists():
        problems.append(f"{path.name}: missing")
        return []
    parsed = _parse(path, ControlRelationshipsFile.model_validate, problems)
    return parsed.relationships if parsed else []


def _check_relationships(entities: list[Entity], relationships: list[ControlRelationship], problems: list[str]) -> None:
    by_id = {entity.id: entity for entity in entities}
    for relationship in relationships:
        label = f"{CONTROL_RELATIONSHIPS_FILE}: {relationship.controller} -> {relationship.controlled}"
        for role, entity_id in (("controller", relationship.controller), ("controlled", relationship.controlled)):
            if entity_id not in by_id:
                problems.append(f"{label}: {role} {entity_id!r} is not in the catalogue")
        controlled = by_id.get(relationship.controlled)
        if isinstance(controlled, Individual):
            problems.append(f"{label}: the controlled Entity must be a Legal Entity, not an Individual")


def _parse[T](path: Path, validate: Callable[[object], T], problems: list[str]) -> T | None:
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
        return validate(data)
    except tomllib.TOMLDecodeError as error:
        problems.append(f"{path.name}: {error}")
    except ValidationError as error:
        problems.extend(f"{path.name}: {line}" for line in _format(error))
    return None


def _format(error: ValidationError) -> Iterator[str]:
    for item in error.errors():
        location = ".".join(str(part) for part in item["loc"]) or "<root>"
        yield f"{location}: {item['msg']}"
