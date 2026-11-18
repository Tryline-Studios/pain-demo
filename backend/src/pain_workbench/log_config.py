"""Structured logging with structlog (spec section 14).

Everything, including uvicorn's own loggers, flows through one stdlib root handler whose formatter renders structlog
events as JSON lines or coloured console lines. uvicorn's access log is switched off: the request middleware emits
the one event per request instead.
"""

import logging
import sys

import structlog

from pain_workbench.settings import LogFormat, Settings

UVICORN_LOGGERS = ("uvicorn", "uvicorn.error")
UVICORN_ACCESS_LOGGER = "uvicorn.access"


def _renderer(log_format: LogFormat) -> structlog.typing.Processor:
    if log_format == "json":
        return structlog.processors.JSONRenderer()
    return structlog.dev.ConsoleRenderer()


def configure_logging(settings: Settings) -> None:
    shared: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]
    if settings.log_format == "json":
        shared.append(structlog.processors.format_exc_info)

    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, _renderer(settings.log_format)],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)

    # uvicorn installs its own handlers before it imports the app; route its error logger through ours instead.
    for name in UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
    access = logging.getLogger(UVICORN_ACCESS_LOGGER)
    access.handlers = []
    access.propagate = False
    access.disabled = True
