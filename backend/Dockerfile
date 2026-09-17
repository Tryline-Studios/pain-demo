# Stage 1: resolve the locked environment with uv (spec 2.2).
FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

# Stage 2: the runtime image has only the virtualenv, no uv, no git; the build passes the commit in.
FROM python:3.13-slim
ARG GIT_SHA=unknown
ENV PAIN_DEMO_GIT_SHA=${GIT_SHA} PATH="/app/.venv/bin:${PATH}" PYTHONUNBUFFERED=1
RUN useradd --system --create-home --uid 1000 app
WORKDIR /app
COPY --from=build --chown=app:app /app/.venv /app/.venv
USER app
EXPOSE 8000
CMD ["uvicorn", "pain_demo.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
