"""FastAPI application factory."""

from fastapi import FastAPI

from pain_demo.api.v1 import meta
from pain_demo.body_limit import BodyLimitMiddleware
from pain_demo.logging import configure_logging
from pain_demo.problems import install_problem_handlers
from pain_demo.request_context import RequestContextMiddleware
from pain_demo.settings import Settings
from pain_demo.version import generator_version

API_PREFIX = "/api/v1"
HEALTH_PATH = f"{API_PREFIX}/health"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings)

    app = FastAPI(title="pain-demo")
    app.state.settings = settings
    app.state.generator_version = generator_version(git_sha=settings.git_sha)
    install_problem_handlers(app)
    # Added innermost first: the request context wraps everything else.
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(RequestContextMiddleware, quiet_paths=frozenset({HEALTH_PATH}))
    app.include_router(meta.router, prefix=API_PREFIX)
    return app
