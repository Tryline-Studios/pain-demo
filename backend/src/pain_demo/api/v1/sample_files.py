"""The `sample-files` endpoints: generation and what a client needs to build a request (spec 12.1)."""

import json
from collections.abc import Callable
from decimal import Decimal
from typing import Annotated, Any, Literal, get_args

import structlog
from fastapi import APIRouter, File, Form, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError
from starlette.concurrency import run_in_threadpool

from pain_demo.catalogue.capabilities import (
    AGENT_PLACEMENTS,
    FILE_LEVEL_PLACEMENTS,
    PLACEMENT_ELIGIBILITY,
    NameVariant,
    Placement,
)
from pain_demo.generation import sample_file, supplied_csv
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
from pain_demo.generation.supplied import Location, catalogue_errors
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
    return await _generate(
        request, body, format, data_source="supplied" if body.payment or body.transactions else "generated"
    )


@router.post(
    "/sample-files/csv",
    operation_id="generate_sample_file_from_csv",
    summary="Generate a Sample File and its Answer Key from Supplied Data as CSV",
    response_model=GeneratedSampleFile,
    responses={
        200: {
            "description": "As `POST /sample-files`",
            "content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}},
        },
        **BODY_TOO_LARGE,
        **VALIDATION_ERROR,
        **BUILD_FAILED,
    },
)
async def generate_sample_file_from_csv(
    request: Request,
    settings: Annotated[
        str,
        Form(
            alias="request",
            description="The generation settings and Hits as `POST /sample-files` takes them, without Supplied Data",
        ),
    ],
    supplied_data: Annotated[
        UploadFile,
        File(description="One row per transaction; columns are dotted field paths such as `creditor.name`"),
    ],
    format: Literal["json", "zip"] = "json",
) -> GeneratedSampleFile | Response:
    try:
        raw = json.loads(settings)
    except ValueError as error:
        raise RequestValidationError(
            [{"loc": ("body", "request"), "msg": f"not JSON: {error}", "type": "json_invalid"}]
        ) from error
    if not isinstance(raw, dict):
        raise RequestValidationError([{"loc": ("body", "request"), "msg": "not a JSON object", "type": "dict_type"}])
    if misplaced := [key for key in ("payment", "transactions") if key in raw]:
        raise RequestValidationError(
            [
                {"loc": ("body", "request", key), "msg": "Supplied Data goes in the CSV", "type": "extra_forbidden"}
                for key in misplaced
            ]
        )
    try:
        rows = await run_in_threadpool(supplied_csv.parse, await supplied_data.read())
        body = GenerationRequest.model_validate({**raw, **rows})
    except supplied_csv.CsvInvalid as invalid:
        raise RequestValidationError(invalid.errors) from invalid
    except ValidationError as invalid:
        raise RequestValidationError(_relocated(invalid.errors(), supplied_csv.locate)) from invalid
    return await _generate(request, body, format, data_source="csv", locate=supplied_csv.locate)


def _relocated(errors: list[Any], locate: Callable[[Location], Location]) -> list[dict[str, Any]]:
    return [{**error, "loc": locate(tuple(error["loc"]))} for error in errors]


async def _generate(
    request: Request,
    body: GenerationRequest,
    format: Literal["json", "zip"],
    data_source: str,
    locate: Callable[[Location], Location] = lambda location: location,
) -> GeneratedSampleFile | Response:
    """Generate for either endpoint; `locate` puts an error's location in the caller's terms."""
    state = request.app.state
    screen = NameScreen(state.catalogue)
    if errors := await run_in_threadpool(catalogue_errors, body.payment, body.transactions, screen):
        raise RequestValidationError(_relocated(errors, locate))
    effective = body.resolve()
    add_log_fields(
        request,
        message_version=effective.message_version,
        transaction_count=effective.transaction_count,
        hit_count=effective.hit_count,
        named_hit_count=len(effective.hits),
        data_source=data_source,
        seed=effective.seed,
    )
    try:
        generated = await run_in_threadpool(
            sample_file.generate,
            effective,
            state.catalogue,
            state.clean_banks,
            screen,
            state.generator_version,
        )
    except HitsInvalid as invalid:
        raise RequestValidationError(_relocated(invalid.errors, locate)) from invalid
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
    supplied_data_columns: list[str] = Field(
        description="The `POST /sample-files/csv` header template; each list at position 0, later ones are `.1`, `.2`"
    )


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
        supplied_data_columns=supplied_csv.columns(),
    )
