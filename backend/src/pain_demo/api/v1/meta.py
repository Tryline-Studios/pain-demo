"""The `meta` endpoints: health and Generator Version."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from pain_demo.version import GeneratorVersion

router = APIRouter(tags=["meta"])


class Health(BaseModel):
    status: str


@router.get("/health", operation_id="get_health", summary="Compose healthcheck")
def get_health() -> Health:
    return Health(status="ok")


@router.get("/version", operation_id="get_version", summary="The Generator Version block")
def get_version(request: Request) -> GeneratorVersion:
    return request.app.state.generator_version
