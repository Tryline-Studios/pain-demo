"""The `validation` endpoint: Upload Validation of an Uploaded Message (spec section 17)."""

from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.datastructures import UploadFile

from pain_demo import validation
from pain_demo.problems import BODY_TOO_LARGE, SERVICE_UNAVAILABLE, UNSUPPORTED_MEDIA_TYPE, VALIDATION_ERROR
from pain_demo.request_context import add_log_fields
from pain_demo.validation import ValidationReport

router = APIRouter(tags=["validation"])

# The route reads the body itself to accept two content types, so FastAPI cannot infer the request body schema.
_REQUEST_BODY = {
    "required": True,
    "content": {
        "multipart/form-data": {
            "schema": {
                "type": "object",
                "required": ["file"],
                "properties": {"file": {"type": "string", "format": "binary"}},
            }
        },
        "application/xml": {"schema": {"type": "string", "format": "binary"}},
    },
}


async def _read_upload(request: Request) -> tuple[bytes, str | None]:
    """The Uploaded Message's bytes and file name (None for a raw body); 415 for any other content type."""
    media_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
    if media_type == "application/xml":
        return await request.body(), None
    if media_type == "multipart/form-data":
        async with request.form() as form:
            upload = form.get("file")
            if isinstance(upload, UploadFile):
                return await upload.read(), upload.filename
            return b"", None
    raise HTTPException(
        HTTPStatus.UNSUPPORTED_MEDIA_TYPE, detail="Send multipart/form-data with a `file` part, or application/xml"
    )


@router.post(
    "/validations",
    operation_id="validate_message",
    summary="Validate an Uploaded Message: always 200 with a Validation Report",
    responses={**BODY_TOO_LARGE, **UNSUPPORTED_MEDIA_TYPE, **VALIDATION_ERROR, **SERVICE_UNAVAILABLE},
    openapi_extra={"requestBody": _REQUEST_BODY},
)
async def validate_message(request: Request) -> ValidationReport:
    content, name = await _read_upload(request)
    if not content:
        raise RequestValidationError(
            [{"loc": ("body", "file"), "msg": "A non-empty file is required", "type": "missing"}]
        )
    try:
        report = await validation.validate(content, name)
    except validation.WorkerUnavailable:
        detail = f"The schema check's worker did not start within {validation.XSD_START_SECONDS:g} seconds; try again"
        raise HTTPException(HTTPStatus.SERVICE_UNAVAILABLE, detail=detail) from None
    add_log_fields(
        request,
        message_version=report.message_version,
        valid=report.valid,
        problem_count=len(report.problems),
        problem_codes=sorted({p.code.value for p in report.problems}),
        size_bytes=report.file.size_bytes,
        sha256=report.file.sha256,
    )
    return report
