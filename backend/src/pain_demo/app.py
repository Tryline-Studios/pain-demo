"""FastAPI application factory."""

from fastapi import FastAPI

from pain_demo.api.v1 import meta
from pain_demo.body_limit import BodyLimitMiddleware
from pain_demo.log_config import configure_logging
from pain_demo.problems import install_problem_handlers
from pain_demo.request_context import RequestContextMiddleware
from pain_demo.settings import Settings
from pain_demo.version import app_version, generator_version

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings)

    app = FastAPI(title="pain-demo", version=app_version())
    app.state.settings = settings
    app.state.generator_version = generator_version(git_sha=settings.git_sha)
    install_problem_handlers(app)
    app.include_router(meta.router, prefix=API_PREFIX)
    # Added innermost first: the request context wraps everything else.
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(RequestContextMiddleware, quiet_paths=frozenset({str(app.url_path_for("get_health"))}))
    return app
