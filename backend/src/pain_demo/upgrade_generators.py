"""`just upgrade-generators`: bump generator pins, regenerate the goldens and show the diff (spec 15.4).

Each argument is one of the five generator libraries, bare for its latest release or `name==version` for a given
one. The pins stay exact. Review the diff; a changed golden means bumping the app's minor version in the same commit,
then `just goldens` again, since the Answer Keys record the app version (spec 9.5).
"""

import argparse
import re
import subprocess
import sys
from collections.abc import Callable

REQUIREMENTS = {
    "pain001": "pain001[fast]",
    "faker": "Faker",
    "schwifty": "schwifty",
    "iuliia": "iuliia",
    "rapidfuzz": "rapidfuzz",
}
"""Each generator library by its normalised name, spelled as `pyproject.toml` spells it."""
PIN = re.compile(r"(?P<name>[A-Za-z0-9_.-]+)(==(?P<version>[A-Za-z0-9_.+!-]+))?")


def run_checked(command: list[str]) -> None:
    subprocess.run(command, check=True)  # noqa: S603 - fixed commands, package names checked against REQUIREMENTS


def commands(pins: list[str], parser: argparse.ArgumentParser) -> list[list[str]]:
    upgrade: list[str] = []
    add: list[str] = []
    for pin in pins:
        match = PIN.fullmatch(pin)
        key = match and match["name"].lower()
        if not match or key not in REQUIREMENTS:
            parser.error(f"{pin!r} is not one of {', '.join(REQUIREMENTS)}, bare or as name==version")
        requirement = REQUIREMENTS[key]
        name = requirement.split("[", 1)[0]
        upgrade += ["--upgrade-package", name]
        add.append(f"{requirement}=={match['version']}" if match["version"] else requirement)
    return [
        ["uv", "add", "--bounds", "exact", *upgrade, *add],
        ["env", "UPDATE_GOLDENS=1", "uv", "run", "pytest", "tests/test_goldens.py"],
        ["git", "--no-pager", "diff", "--stat", "--", "."],
        ["git", "--no-pager", "diff", "--", "pyproject.toml", "tests/goldens"],
    ]


def main(argv: list[str] | None = None, run: Callable[[list[str]], object] = run_checked) -> int:
    parser = argparse.ArgumentParser(prog="just upgrade-generators", description=__doc__.splitlines()[0])
    parser.add_argument("pins", nargs="+", metavar="library[==version]")
    for command in commands(parser.parse_args(argv).pins, parser):
        run(command)
    print("\nReview the diff. A changed golden bumps the minor version in pyproject.toml; then rerun `just goldens`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
