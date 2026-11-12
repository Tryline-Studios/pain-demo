"""The `sample-files` endpoints: generation and what a client needs to build a request (spec 12.1)."""

from decimal import Decimal
from typing import get_args

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from pain_demo.generation import sample_file
from pain_demo.generation.clean_banks import SUPPORTED_COUNTRIES, SupportedCountry
from pain_demo.generation.request import (
    CURRENCY_BY_COUNTRY,
    DEFAULT_AMOUNT_MAX,
    DEFAULT_AMOUNT_MIN,
    DEFAULT_COUNTRIES,
    DEFAULT_MESSAGE_VERSION,
    DEFAULT_TRANSACTION_COUNT,
    MAX_SEED_LENGTH,
    MAX_TRANSACTIONS,
    GenerationRequest,
    MessageVersion,
)
from pain_demo.generation.sample_file import GeneratedSampleFile
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
    responses={**BODY_TOO_LARGE, **VALIDATION_ERROR, **BUILD_FAILED},
)
async def generate_sample_file(request: Request, body: GenerationRequest) -> GeneratedSampleFile:
    effective = body.resolve()
    state = request.app.state
    add_log_fields(
        request,
        message_version=effective.message_version,
        transaction_count=effective.transaction_count,
        hit_count=0,
        named_hit_count=0,
        data_source="generated",
        seed=effective.seed,
    )
    try:
        generated = await run_in_threadpool(
            sample_file.generate, effective, state.clean_banks, NameScreen(state.catalogue), state.generator_version
        )
    except RenderFailed as error:
        add_log_fields(request, outcome="build_failed")
        log.error("build_failed", xsd_messages=error.messages, effective_request=effective.model_dump(mode="json"))
        raise
    add_log_fields(request, outcome="generated", warning_count=len(generated.answer_key.warnings))
    return generated


class MessageVersionOption(BaseModel):
    message_version: MessageVersion
    default: bool


class CountryOption(BaseModel):
    country: SupportedCountry
    currency: str = Field(description="What a creditor in this country is paid in when `currencies` is absent")


class Limits(BaseModel):
    max_transactions: int
    max_seed_length: int


class Defaults(BaseModel):
    message_version: MessageVersion
    transaction_count: int
    countries: list[SupportedCountry]
    amount_min: Decimal
    amount_max: Decimal


class Options(BaseModel):
    countries: list[CountryOption]
    limits: Limits
    defaults: Defaults


@router.get("/message-versions", operation_id="list_message_versions", summary="The eleven Message Versions")
def list_message_versions() -> list[MessageVersionOption]:
    return [
        MessageVersionOption(message_version=version, default=version == DEFAULT_MESSAGE_VERSION)
        for version in get_args(MessageVersion.__value__)
    ]


@router.get("/options", operation_id="get_options", summary="What a generation request may ask for, and its defaults")
def get_options() -> Options:
    return Options(
        countries=[CountryOption(country=c, currency=CURRENCY_BY_COUNTRY[c]) for c in SUPPORTED_COUNTRIES],
        limits=Limits(max_transactions=MAX_TRANSACTIONS, max_seed_length=MAX_SEED_LENGTH),
        defaults=Defaults(
            message_version=DEFAULT_MESSAGE_VERSION,
            transaction_count=DEFAULT_TRANSACTION_COUNT,
            countries=list(DEFAULT_COUNTRIES),
            amount_min=DEFAULT_AMOUNT_MIN,
            amount_max=DEFAULT_AMOUNT_MAX,
        ),
    )
