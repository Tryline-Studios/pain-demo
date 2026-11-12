from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from pain_demo import validation
from pain_demo.app import create_app

ROSTER: dict[str, list[str]] = {
    "bank": [
        "sberbank",
        "vtb-bank",
        "gazprombank",
        "alfa-bank",
        "bank-rossiya",
        "promsvyazbank",
        "veb-rf",
        "russian-agricultural-bank",
        "t-bank",
        "sberbank-europe",
        "evrofinance-mosnarbank",
        "bank-dabrabyt",
        "belinvestbank",
        "alfa-bank-belarus",
        "bank-melli-iran",
        "bank-mellat",
        "bank-sepah",
        "foreign-trade-bank-dprk",
        "daedong-credit-bank",
        "bandes",
    ],
    "corporate": [
        "evraz-plc",
        "evraz-ntmk",
        "rosneft",
        "rostec",
        "gazprom-neft",
        "sovcomflot",
        "alrosa",
        "belaruskali",
        "national-iranian-oil-company",
        "irisl",
        "mahan-air",
        "komid",
        "dandong-hongxiang",
        "pdvsa",
        "cham-holding",
        "syriatel",
    ],
    "individual": [
        "roman-abramovich",
        "alexander-abramov",
        "andrey-kostin",
        "herman-gref",
        "andrey-akimov",
        "mikhail-fridman",
        "yuri-kovalchuk",
        "igor-sechin",
        "sergey-chemezov",
        "rami-makhlouf",
        "fares-chehabi",
        "ahmad-derakhshandeh",
        "simon-zerpa",
        "kim-chol-sam",
    ],
}
"""The approved v1 roster ids by Entity Type, in spec section 3.2 order."""


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as client:
        yield client


@pytest.fixture
def roster() -> dict[str, list[str]]:
    return ROSTER


@pytest.fixture
def roster_ids() -> list[str]:
    """Every roster id, in the id order the catalogue and `GET /entities` use."""
    return sorted(entity_id for ids in ROSTER.values() for entity_id in ids)


@pytest.fixture(autouse=True, scope="session")
def _stop_xsd_workers() -> Iterator[None]:
    """Direct `validate_message` calls start workers outside any app's lifespan."""
    yield
    validation.shutdown()
