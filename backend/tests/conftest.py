from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from pain_demo.app import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as client:
        yield client


@pytest.fixture
def starter_ids() -> list[str]:
    """The shipped starter Entities, in id order (ticket #26 grows this to the full roster)."""
    return [
        "bank-melli-iran",
        "evraz-ntmk",
        "evraz-plc",
        "kim-chol-sam",
        "roman-abramovich",
        "russian-agricultural-bank",
        "sberbank",
        "sberbank-europe",
    ]
