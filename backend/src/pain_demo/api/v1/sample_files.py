"""The `sample-files` endpoints: generation and what a client needs to build a request (spec 12.1)."""

import structlog
from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from pain_demo.generation import sample_file
from pain_demo.generation.request import GenerationRequest
from pain_demo.generation.sample_file import GeneratedSampleFile
from pain_demo.generation.screening import NameScreen
from pain_demo.problems import BuildFailed
from pain_demo.renderer import RenderFailed
from pain_demo.request_context import add_log_fields

router = APIRouter(tags=["sample-files"])

log = structlog.get_logger("pain_demo.generation")


@router.post(
    "/sample-files",
    operation_id="generate_sample_file",
    summary="Generate a Sample File and its Answer Key",
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
        raise BuildFailed(str(error)) from error
    add_log_fields(request, outcome="generated", warning_count=len(generated.answer_key.warnings))
    return generated
