"""Files validated at startup (spec 14.5): every problem is collected before the process refuses to start."""

import tomllib
from collections.abc import Callable, Iterator
from pathlib import Path

from pydantic import ValidationError


class FileProblems(Exception):
    """A file on disk is not usable; `problems` lists every reason."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def parse_toml[T](path: Path, validate: Callable[[object], T], problems: list[str]) -> T | None:
    """Parse and validate one TOML file, appending each problem as `<file>: <location>: <message>`."""
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
        return validate(data)
    except tomllib.TOMLDecodeError as error:
        problems.append(f"{path.name}: {error}")
    except ValidationError as error:
        problems.extend(f"{path.name}: {line}" for line in _format(error))
    return None


def _format(error: ValidationError) -> Iterator[str]:
    for item in error.errors():
        location = ".".join(str(part) for part in item["loc"]) or "<root>"
        yield f"{location}: {item['msg']}"
