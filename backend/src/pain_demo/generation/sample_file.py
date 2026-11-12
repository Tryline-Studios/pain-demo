"""One Sample File and its Answer Key from an Effective Request (spec 9.4, 11, 12.2)."""

import hashlib
import io
import json
import re
import zipfile
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from pain_demo.catalogue import Catalogue
from pain_demo.generation.clean_banks import CleanBankList
from pain_demo.generation.exposures import Exposure, by_exposure_country, place_exposures
from pain_demo.generation.generated_data import GeneratedData
from pain_demo.generation.hits import Hit, place_hits, summary_counts
from pain_demo.generation.request import EffectiveRequest, MessageVersion
from pain_demo.generation.screening import NameScreen
from pain_demo.renderer import render
from pain_demo.version import GeneratorVersion

ANSWER_KEY_VERSION = 1
_FILENAME_SAFE = re.compile(r"[A-Za-z0-9._-]+")
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


class SampleFile(BaseModel):
    filename: str
    content_type: Literal["application/xml"] = "application/xml"
    xml: str

    @property
    def answer_key_filename(self) -> str:
        """`<name>.answer-key.json` beside `<name>.xml` (spec 12.2)."""
        return self.filename.removesuffix(".xml") + ".answer-key.json"

    @property
    def zip_filename(self) -> str:
        """`<name>.zip` (spec 12.2)."""
        return self.filename.removesuffix(".xml") + ".zip"


class FileFacts(BaseModel):
    message_id: str
    created_at: datetime
    execution_date: date
    transaction_count: int
    hit_count: int
    sha256: str
    """Of the Sample File's UTF-8 XML bytes, leading comment included."""


class Summary(BaseModel):
    by_placement: dict[str, int] = {}
    by_name_variant: dict[str, int] = {}
    by_entity_type: dict[str, int] = {}
    by_list: dict[str, int] = {}
    by_exposure_country: dict[str, int] = {}


class AnswerKeyTransaction(BaseModel):
    number: int
    end_to_end_id: str
    hit_ids: list[str]


class AnswerKey(BaseModel):
    """Key order is the wire order (spec 11.2)."""

    answer_key_version: Literal[1] = ANSWER_KEY_VERSION
    seed: str
    message_version: MessageVersion
    generator: GeneratorVersion
    request: EffectiveRequest
    file: FileFacts
    summary: Summary
    hits: list[Hit]
    exposures: list[Exposure]
    transactions: list[AnswerKeyTransaction]
    warnings: list[str]
    """Elements of Generated Data the Message Version could not carry and the build dropped."""


class GeneratedSampleFile(BaseModel):
    sample_file: SampleFile
    answer_key: AnswerKey


def answer_key_json(answer_key: AnswerKey) -> str:
    """The canonical file form: 2-space indent and a trailing newline (spec 11.1)."""
    return answer_key.model_dump_json(indent=2) + "\n"


def zip_bytes(generated: GeneratedSampleFile) -> bytes:
    """`<name>.xml` and `<name>.answer-key.json` (spec 12.2), with fixed timestamps so the same file zips the same."""
    sample_file = generated.sample_file
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for member, text in (
            (sample_file.filename, sample_file.xml),
            (sample_file.answer_key_filename, answer_key_json(generated.answer_key)),
        ):
            archive.writestr(zipfile.ZipInfo(member, date_time=_ZIP_EPOCH), text, zipfile.ZIP_DEFLATED)
    return buffer.getvalue()


def filename(message_version: MessageVersion, seed: str) -> str:
    """`<message_version>-<seed>.xml`, with a Seed outside `[A-Za-z0-9._-]` replaced by a hash of it (spec 12.2)."""
    safe = seed if _FILENAME_SAFE.fullmatch(seed) else hashlib.sha256(seed.encode()).hexdigest()[:16]
    return f"{message_version}-{safe}.xml"


def provenance_comment(seed: str, generator: GeneratorVersion) -> str:
    """The one-line comment after the XML declaration (spec 9.4). The Seed is JSON-encoded, ASCII only, with `-`
    escaped where two would meet, so the comment stays well-formed and `json.loads` gives the exact Seed back."""
    encoded = re.sub(r"-(?=-)", r"\\u002d", json.dumps(seed))
    return f"<!-- pain-demo {generator.app_version} seed={encoded} -->"


def generate(
    request: EffectiveRequest,
    catalogue: Catalogue,
    clean_banks: CleanBankList,
    screen: NameScreen,
    generator: GeneratorVersion,
) -> GeneratedSampleFile:
    """Blocking: run it in a worker thread."""
    data = GeneratedData(request, clean_banks, screen)
    model, hits = place_hits(data.sample_file_model(), request, catalogue, data)
    model, exposures = place_exposures(model, request, hits, data)
    file_hit_ids = [hit.id for hit in hits if hit.scope == "file"]
    rendered = render(model)
    declaration, _, body = rendered.xml.decode("utf-8").partition("\n")
    xml = f"{declaration}\n{provenance_comment(request.seed, generator)}\n{body}"
    answer_key = AnswerKey(
        seed=request.seed,
        message_version=request.message_version,
        generator=generator,
        request=request,
        file=FileFacts(
            message_id=model.message_id,
            created_at=model.created_at,
            execution_date=model.execution_date,
            transaction_count=len(model.transactions),
            hit_count=len(hits),
            sha256=hashlib.sha256(xml.encode("utf-8")).hexdigest(),
        ),
        summary=Summary(**summary_counts(hits, catalogue), by_exposure_country=by_exposure_country(exposures)),
        hits=hits,
        exposures=exposures,
        transactions=[
            AnswerKeyTransaction(
                number=number,
                end_to_end_id=tx.end_to_end_id,
                # A sanctioned Debtor or Debtor Agent touches every transaction, so a tool may rightly alert on each.
                hit_ids=[*file_hit_ids, *(hit.id for hit in hits if hit.transaction_number == number)],
            )
            for number, tx in enumerate(model.transactions, start=1)
        ],
        warnings=[f"{path} dropped: not in {request.message_version}" for path in rendered.dropped],
    )
    return GeneratedSampleFile(
        sample_file=SampleFile(filename=filename(request.message_version, request.seed), xml=xml),
        answer_key=answer_key,
    )
