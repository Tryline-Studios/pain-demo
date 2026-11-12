"""`just upgrade-generators` (spec 15.4), with the commands faked: the tests never resolve or install anything."""

import pytest

from pain_demo import upgrade_generators


def upgrade(*argv: str) -> list[list[str]]:
    commands: list[list[str]] = []
    assert upgrade_generators.main(list(argv), run=commands.append) == 0
    return commands


def test_it_bumps_the_named_pins_to_the_latest_then_regenerates_the_goldens_and_shows_the_diff() -> None:
    bump, goldens, *diffs = upgrade("faker", "pain001")

    assert bump == [
        "uv",
        "add",
        "--bounds",
        "exact",
        "--upgrade-package",
        "Faker",
        "--upgrade-package",
        "pain001",
        "Faker",
        "pain001[fast]",
    ]
    assert goldens[-2:] == ["pytest", "tests/test_goldens.py"]
    assert "UPDATE_GOLDENS=1" in goldens
    assert diffs[-1][:3] == ["git", "--no-pager", "diff"]


def test_a_given_version_is_pinned_exactly() -> None:
    bump, *_ = upgrade("rapidfuzz==3.15.0", "IUliia")

    assert bump[-2:] == ["rapidfuzz==3.15.0", "iuliia"]
    assert bump.count("--upgrade-package") == 2


@pytest.mark.parametrize("argv", [[], ["fastapi"], ["faker>=40"]])
def test_only_the_five_generator_libraries_are_accepted(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        upgrade_generators.main(argv, run=lambda command: pytest.fail(f"ran {command}"))
    assert raised.value.code == 2
