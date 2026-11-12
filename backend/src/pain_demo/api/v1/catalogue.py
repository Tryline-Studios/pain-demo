"""The `catalogue` endpoints: the Entity Catalogue listing and detail (spec section 12.1)."""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, TypeAdapter

from pain_demo.catalogue import Catalogue
from pain_demo.catalogue.capabilities import NameVariant, Placement, supported_name_variants, supported_placements
from pain_demo.catalogue.schema import (
    Bank,
    ControlRelationship,
    Corporate,
    CountryCode,
    Entity,
    EntityType,
    Individual,
    SanctionsList,
)
from pain_demo.problems import Problem

router = APIRouter(tags=["catalogue"])


class EntitySummary(BaseModel):
    id: str
    entity_type: EntityType
    display_name: str
    lists: list[SanctionsList]
    countries: list[str] = Field(
        description="A Legal Entity's address countries; an Individual's nationalities and country of residence"
    )
    name_variants: list[NameVariant]
    placements: list[Placement]
    has_bic: bool


class BankDetail(Bank):
    control_relationships: list[ControlRelationship]


class CorporateDetail(Corporate):
    control_relationships: list[ControlRelationship]


class IndividualDetail(Individual):
    control_relationships: list[ControlRelationship]


type EntityDetail = Annotated[BankDetail | CorporateDetail | IndividualDetail, Field(discriminator="entity_type")]

_detail_adapter: TypeAdapter[EntityDetail] = TypeAdapter(EntityDetail)


def summarise(entity: Entity) -> EntitySummary:
    return EntitySummary(
        id=entity.id,
        entity_type=entity.entity_type,
        display_name=entity.display_name,
        lists=entity.lists,
        countries=entity.countries,
        name_variants=supported_name_variants(entity),
        placements=supported_placements(entity.entity_type),
        has_bic=entity.entity_type == "bank" and bool(entity.bics),
    )


def catalogue_of(request: Request) -> Catalogue:
    return request.app.state.catalogue


@router.get("/entities", operation_id="list_entities", summary="The Entity Catalogue, one summary per Entity")
def list_entities(
    request: Request,
    entity_type: Annotated[EntityType | None, Query()] = None,
    sanctions_list: Annotated[SanctionsList | None, Query(alias="list")] = None,
    country: Annotated[CountryCode | None, Query()] = None,
) -> list[EntitySummary]:
    return [
        summarise(entity)
        for entity in catalogue_of(request).entities.values()
        if (entity_type is None or entity.entity_type == entity_type)
        and (sanctions_list is None or sanctions_list in entity.lists)
        and (country is None or country in entity.countries)
    ]


@router.get(
    "/entities/{entity_id}",
    operation_id="get_entity",
    summary="One Entity with every sourced fact",
    responses={HTTPStatus.NOT_FOUND: {"model": Problem, "description": "No Entity with that id"}},
)
def get_entity(request: Request, entity_id: str) -> EntityDetail:
    catalogue = catalogue_of(request)
    entity = catalogue.get(entity_id)
    if entity is None:
        raise HTTPException(HTTPStatus.NOT_FOUND, detail=f"No Entity with id {entity_id!r}")
    detail = {**entity.model_dump(), "control_relationships": catalogue.relationships_of(entity_id)}
    return _detail_adapter.validate_python(detail)
