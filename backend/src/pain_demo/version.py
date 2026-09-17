"""The Generator Version block (spec section 9.4): everything that shapes generated output."""

import importlib.metadata
import subprocess
from datetime import date
from pathlib import Path

from pydantic import BaseModel

APP_DISTRIBUTION = "pain-demo"
UNKNOWN_GIT_SHA = "unknown"


class GeneratorVersion(BaseModel):
    """Recorded in every Answer Key and returned by `GET /version`; key order is the wire order."""

    app_version: str
    git_sha: str
    pain001: str
    faker: str
    schwifty: str
    iuliia: str
    rapidfuzz: str
    catalogue_snapshot: date


def app_version() -> str:
    return importlib.metadata.version(APP_DISTRIBUTION)


def git_sha_from_checkout() -> str:
    """The HEAD commit of the checkout this package is imported from, or `unknown` outside a git checkout."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607 - resolved on PATH on purpose
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
            cwd=Path(__file__).parent,
        )
    except (OSError, subprocess.TimeoutExpired):
        return UNKNOWN_GIT_SHA
    sha = completed.stdout.strip()
    return sha if completed.returncode == 0 and sha else UNKNOWN_GIT_SHA


def generator_version(catalogue_snapshot: date, git_sha: str | None = None) -> GeneratorVersion:
    """Build the block from the installed distributions and the loaded Entity Catalogue's snapshot date."""
    return GeneratorVersion(
        app_version=app_version(),
        git_sha=git_sha or git_sha_from_checkout(),
        pain001=importlib.metadata.version("pain001"),
        faker=importlib.metadata.version("Faker"),
        schwifty=importlib.metadata.version("schwifty"),
        iuliia=importlib.metadata.version("iuliia"),
        rapidfuzz=importlib.metadata.version("rapidfuzz"),
        catalogue_snapshot=catalogue_snapshot,
    )
