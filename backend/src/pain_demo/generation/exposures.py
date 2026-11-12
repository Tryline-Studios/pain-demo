"""Exposures (spec 8, 11.5): clean transactions whose creditor side is moved into a sanctioned or high-risk country.

Overlaid after the Hits, on transactions no Hit touches, from the `exposures` stream (which transactions) and each
transaction's own `tx/<n>/exposure` stream (country, names, agent, account), so Exposures never move a Hit.
"""

from collections import Counter
from dataclasses import replace
from typing import Literal

from pydantic import BaseModel

from pain_demo.generation.exposure_countries import EXPOSURE_COUNTRIES, ExposureCountry
from pain_demo.generation.generated_data import GeneratedData
from pain_demo.generation.hits import Hit
from pain_demo.generation.model import SampleFileModel
from pain_demo.generation.request import EffectiveRequest
from pain_demo.generation.seeds import stream

type ExposedElement = Literal["creditor_address", "agent_bic", "account"]
EXPOSED_ELEMENTS: list[ExposedElement] = ["creditor_address", "agent_bic", "account"]
"""Every Exposure moves all three: the creditor's address, its agent's BIC and the account into the country."""


class Exposure(BaseModel):
    """One exposed transaction (spec 11.2), in wire order."""

    transaction_number: int
    end_to_end_id: str
    country: ExposureCountry
    currency: str
    elements: list[ExposedElement]


_CREDITOR_SIDE = frozenset({"creditor", "creditor_agent", "creditor_account", "currency"})
"""What an Exposure replaces (spec 8.3)."""


def place_exposures(
    model: SampleFileModel, request: EffectiveRequest, hits: list[Hit], data: GeneratedData
) -> tuple[SampleFileModel, list[Exposure]]:
    """Overlay `request.exposure_count` Exposures; the request's validation leaves room for them beside the Hits."""
    taken = {hit.transaction_number for hit in hits}
    free = [number for number in range(1, len(model.transactions) + 1) if number not in taken]
    transactions = list(model.transactions)
    exposures: list[Exposure] = []
    # Supplied creditor sides are kept while there is room elsewhere (spec 5.3); without Supplied Data, one draw.
    supplied = {n for n, row in enumerate(request.transactions, start=1) if row.model_fields_set & _CREDITOR_SIDE}
    rng = stream(request.seed, "exposures")
    preferred = [n for n in free if n not in supplied]
    chosen = rng.sample(preferred, min(request.exposure_count, len(preferred)))
    chosen += rng.sample([n for n in free if n in supplied], request.exposure_count - len(chosen))
    for number in sorted(chosen):
        rng = stream(request.seed, f"tx/{number}/exposure")
        country = rng.choice(request.exposure_countries)
        currency = EXPOSURE_COUNTRIES[country].currency
        agent, account = data.exposed_agent_and_account(rng, country)
        tx = transactions[number - 1]
        transactions[number - 1] = replace(
            tx,
            creditor=data.exposed_party(rng, country),
            creditor_agent=agent,
            creditor_account=account,
            currency=currency,
        )
        exposures.append(
            Exposure(
                transaction_number=number,
                end_to_end_id=tx.end_to_end_id,
                country=country,
                currency=currency,
                elements=EXPOSED_ELEMENTS,
            )
        )
    return replace(model, transactions=tuple(transactions)), exposures


def by_exposure_country(exposures: list[Exposure]) -> dict[str, int]:
    """`summary.by_exposure_country` (spec 11.5)."""
    return dict(sorted(Counter(exposure.country for exposure in exposures).items()))
