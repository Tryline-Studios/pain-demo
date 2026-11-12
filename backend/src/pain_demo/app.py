"""FastAPI application factory."""

from pathlib import Path

import structlog
from fastapi import FastAPI

from pain_demo.api.v1 import catalogue as catalogue_api
from pain_demo.api.v1 import meta
from pain_demo.api.v1 import sample_files as sample_files_api
from pain_demo.api.v1 import validation as validation_api
from pain_demo.body_limit import BodyLimitMiddleware
from pain_demo.catalogue import DEFAULT_ROOT, Catalogue, CatalogueError, load_catalogue
from pain_demo.generation.clean_banks import DEFAULT_PATH, CleanBankList, CleanBankListError, load_clean_banks
from pain_demo.log_config import configure_logging
from pain_demo.problems import PROBLEM_RESPONSES, install_problem_handlers, problem_openapi
from pain_demo.request_context import RequestContextMiddleware
from pain_demo.settings import Settings
from pain_demo.version import app_version, generator_version

API_PREFIX = "/api/v1"
STARTUP_VALIDATION_EXIT_CODE = 1

log = structlog.get_logger("pain_demo.startup")


def create_app(
    settings: Settings | None = None, catalogue_root: Path = DEFAULT_ROOT, clean_banks_path: Path = DEFAULT_PATH
) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings)
    catalogue = _load_catalogue_or_exit(catalogue_root)
    clean_banks = _load_clean_banks_or_exit(clean_banks_path, catalogue)

    app = FastAPI(title="pain-demo", version=app_version(), responses=PROBLEM_RESPONSES)
    app.state.settings = settings
    app.state.catalogue = catalogue
    app.state.clean_banks = clean_banks
    app.state.generator_version = generator_version(catalogue.snapshot_date, git_sha=settings.git_sha)
    install_problem_handlers(app)
    problem_openapi(app)
    app.include_router(sample_files_api.router, prefix=API_PREFIX)
    app.include_router(meta.router, prefix=API_PREFIX)
    app.include_router(catalogue_api.router, prefix=API_PREFIX)
    app.include_router(validation_api.router, prefix=API_PREFIX)
    # Added innermost first: the request context wraps everything else.
    app.add_middleware(
        BodyLimitMiddleware, path_caps={str(app.url_path_for("validate_message")): validation_api.MAX_UPLOAD_BYTES}
    )
    app.add_middleware(RequestContextMiddleware, quiet_paths=frozenset({str(app.url_path_for("get_health"))}))
    return app


def _load_catalogue_or_exit(root: Path) -> Catalogue:
    """Startup validation (spec 3.3 and 14.5): a malformed catalogue is logged at CRITICAL and stops the process."""
    try:
        return load_catalogue(root)
    except CatalogueError as error:
        log.critical("catalogue_invalid", root=str(root), problems=error.problems)
        raise SystemExit(STARTUP_VALIDATION_EXIT_CODE) from error


def _load_clean_banks_or_exit(path: Path, catalogue: Catalogue) -> CleanBankList:
    """Startup validation (spec 4.3): a Clean Bank List that overlaps the catalogue stops the process the same way."""
    try:
        return load_clean_banks(catalogue, path)
    except CleanBankListError as error:
        log.critical("clean_bank_list_invalid", path=str(path), problems=error.problems)
        raise SystemExit(STARTUP_VALIDATION_EXIT_CODE) from error
