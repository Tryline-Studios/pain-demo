"""Runtime configuration: environment variables with the `PAIN_DEMO_` prefix (spec section 16)."""

import sys
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

type LogFormat = Literal["json", "console"]
type LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


def default_log_format() -> LogFormat:
    """Console lines for a developer at a terminal, JSON lines everywhere else."""
    return "console" if sys.stdout.isatty() else "json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PAIN_DEMO_", env_file=".env", extra="ignore")

    log_format: LogFormat = Field(default_factory=default_log_format)
    log_level: LogLevel = "INFO"
    git_sha: str | None = Field(
        default=None,
        description="The commit the running app was built from. Set by the image build; "
        "when unset, read from the git checkout, else reported as `unknown`.",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def _upper_case_log_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value
