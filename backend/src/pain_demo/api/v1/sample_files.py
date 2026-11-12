"""The `sample-files` endpoints: generation and what a client needs to build a request (spec 12.1)."""

from decimal import Decimal
from typing import Literal, get_args

import structlog
from fastapi import APIRouter, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from pain_demo.catalogue.capabilities import (
    AGENT_PLACEMENTS,
    FILE_LEVEL_PLACEMENTS,
    PLACEMENT_ELIGIBILITY,
    NameVariant,
    Placement,
)
from pain_demo.generation import sample_file
from pain_demo.generation.clean_banks import SUPPORTED_COUNTRIES, SupportedCountry
from pain_demo.generation.exposure_countries import EXPOSURE_COUNTRIES, ExposureCountry
from pain_demo.generation.generated_data import COUNTRIES
from pain_demo.generation.named_hits import HitsInvalid
from pain_demo.generation.request import (
    DEFAULT_AMOUNT_MAX,
    DEFAULT_AMOUNT_MIN,
    DEFAULT_COUNTRIES,
    DEFAULT_MESSAGE_VERSION,
    DEFAULT_TRANSACTION_COUNT,
    MAX_SEED_LENGTH,
    MAX_TRANSACTIONS,
    MESSAGE_VERSIONS,
    RENDERING_MODES,
    GenerationRequest,
    MessageVersion,
    RenderingMode,
)
from pain_demo.generation.sample_file import AnswerKey, GeneratedSampleFile, answer_key_csv, zip_bytes
from pain_demo.generation.screening import NameScreen
from pain_demo.problems import BODY_TOO_LARGE, BUILD_FAILED, VALIDATION_ERROR
from pain_demo.renderer import RenderFailed
from pain_demo.request_context import add_log_fields

router = APIRouter(tags=["sample-files"])

log = structlog.get_logger("pain_demo.generation")


@router.post(
    "/sample-files",
    operation_id="generate_sample_file",
    summary="Generate a Sample File and its Answer Key",
    response_model=GeneratedSampleFile,
    responses={
        200: {
            "description": "The JSON envelope, or with `format=zip` a zip of `<name>.xml`, `<name>.answer-key.json`"
            " and `<name>.answer-key.csv`",
            "content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}},
        },
        **BODY_TOO_LARGE,
        **VALIDATION_ERROR,
        **BUILD_FAILED,
    },
)
async def generate_sample_file(
    request: Request, body: GenerationRequest, format: Literal["json", "zip"] = "json"
) -> GeneratedSampleFile | Response:
    effective = body.resolve()
    state = request.app.state
    add_log_fields(
        request,
        message_version=effective.message_version,
        transaction_count=effective.transaction_count,
        hit_count=effective.hit_count,
        named_hit_count=len(effective.hits),
        data_source="generated",
        seed=effective.seed,
    )
    try:
        generated = await run_in_threadpool(
            sample_file.generate,
            effective,
            state.catalogue,
            state.clean_banks,
            NameScreen(state.catalogue),
            state.generator_version,
        )
    except HitsInvalid as invalid:
        raise RequestValidationError(invalid.errors) from invalid
    except RenderFailed as error:
        add_log_fields(request, outcome="build_failed")
        log.error("build_failed", xsd_messages=error.messages, effective_request=effective.model_dump(mode="json"))
        raise
    add_log_fields(request, outcome="generated", warning_count=len(generated.answer_key.warnings))
    if format == "zip":
        return Response(
            zip_bytes(generated),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{generated.sample_file.zip_filename}"'},
        )
    return generated


@router.post(
    "/answer-keys/csv",
    operation_id="answer_key_to_csv",
    summary="The CSV projection of an Answer Key's hits",
    response_class=Response,
    responses={
        200: {"description": "One row per Hit (spec 11.1)", "content": {"text/csv": {"schema": {"type": "string"}}}},
        **BODY_TOO_LARGE,
        **VALIDATION_ERROR,
    },
)
def answer_key_to_csv(answer_key: AnswerKey) -> Response:
    """A pure transform: any Answer Key of the current `answer_key_version`; another version is a 422."""
    return Response(answer_key_csv(answer_key), media_type="text/csv; charset=utf-8")


class MessageVersionOption(BaseModel):
    message_version: MessageVersion
    default: bool


class CountryOption(BaseModel):
    country: SupportedCountry
    currency: str = Field(description="What a creditor in this country is paid in when `currencies` is absent")


class ExposureCountryOption(BaseModel):
    country: ExposureCountry
    currency: str = Field(description="What an exposed transaction is paid in, whatever `currencies` says")


class Limits(BaseModel):
    max_transactions: int
    max_seed_length: int


class Defaults(BaseModel):
    message_version: MessageVersion
    transaction_count: int
    countries: list[SupportedCountry]
    amount_min: Decimal
    amount_max: Decimal
    exposure_countries: list[ExposureCountry]


class PlacementOption(BaseModel):
    placement: Placement
    file_level: bool = Field(description="Debtor and Debtor Agent: one per file, and a named Hit takes no transaction")
    agent: bool = Field(description="Takes a rendering mode")


class Options(BaseModel):
    countries: list[CountryOption]
    placements: list[PlacementOption]
    name_variants: list[NameVariant]
    rendering_modes: list[RenderingMode]
    exposure_countries: list[ExposureCountryOption]
    limits: Limits
    defaults: Defaults


@router.get("/message-versions", operation_id="list_message_versions", summary="The eleven Message Versions")
def list_message_versions() -> list[MessageVersionOption]:
    return [
        MessageVersionOption(message_version=version, default=version == DEFAULT_MESSAGE_VERSION)
        for version in MESSAGE_VERSIONS
    ]


@router.get("/options", operation_id="get_options", summary="What a generation request may ask for, and its defaults")
def get_options() -> Options:
    return Options(
        countries=[CountryOption(country=c, currency=COUNTRIES[c].currency) for c in SUPPORTED_COUNTRIES],
        placements=[
            PlacementOption(placement=p, file_level=p in FILE_LEVEL_PLACEMENTS, agent=p in AGENT_PLACEMENTS)
            for p in PLACEMENT_ELIGIBILITY
        ],
        name_variants=list(get_args(NameVariant.__value__)),
        rendering_modes=list(RENDERING_MODES),
        exposure_countries=[
            ExposureCountryOption(country=c, currency=p.currency) for c, p in EXPOSURE_COUNTRIES.items()
        ],
        limits=Limits(max_transactions=MAX_TRANSACTIONS, max_seed_length=MAX_SEED_LENGTH),
        defaults=Defaults(
            message_version=DEFAULT_MESSAGE_VERSION,
            transaction_count=DEFAULT_TRANSACTION_COUNT,
            countries=list(DEFAULT_COUNTRIES),
            amount_min=DEFAULT_AMOUNT_MIN,
            amount_max=DEFAULT_AMOUNT_MAX,
            exposure_countries=list(EXPOSURE_COUNTRIES),
        ),
    )
