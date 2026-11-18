import sys

import pytest
from pydantic import ValidationError

from pain_workbench.settings import Settings


def test_settings_read_the_pain_workbench_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAIN_WORKBENCH_LOG_FORMAT", "console")
    monkeypatch.setenv("PAIN_WORKBENCH_LOG_LEVEL", "DEBUG")

    settings = Settings()

    assert settings.log_format == "console"
    assert settings.log_level == "DEBUG"


def test_log_level_defaults_to_info(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PAIN_WORKBENCH_LOG_LEVEL", raising=False)

    assert Settings().log_level == "INFO"


def test_log_level_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAIN_WORKBENCH_LOG_LEVEL", "debug")

    assert Settings().log_level == "DEBUG"


def test_log_format_defaults_to_console_on_a_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PAIN_WORKBENCH_LOG_FORMAT", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    assert Settings().log_format == "console"


def test_log_format_defaults_to_json_off_a_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PAIN_WORKBENCH_LOG_FORMAT", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    assert Settings().log_format == "json"


def test_an_unknown_log_format_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAIN_WORKBENCH_LOG_FORMAT", "xml")

    with pytest.raises(ValidationError):
        Settings()
