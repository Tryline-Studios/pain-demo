"""The generation request (spec 5.1, 5.5, 12.4) and its Effective Request (spec 5.7).

Only the generation settings, the Hit Count and Exposures exist so far; named Hits and Supplied Data arrive with
their own tickets.
"""

import secrets
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal, get_args

import pycountry
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from pain_demo.generation.clean_banks import SupportedCountry
from pain_demo.generation.exposure_countries import EXPOSURE_COUNTRIES, ExposureCountry
from pain_demo.generation.seeds import identifier, stream

type MessageVersion = Literal[
    "pain.001.001.03",
    "pain.001.001.04",
    "pain.001.001.05",
    "pain.001.001.06",
    "pain.001.001.07",
    "pain.001.001.08",
    "pain.001.001.09",
    "pain.001.001.10",
    "pain.001.001.11",
    "pain.001.001.12",
    "pain.001.001.13",
]

MESSAGE_VERSIONS: tuple[MessageVersion, ...] = get_args(MessageVersion.__value__)
DEFAULT_MESSAGE_VERSION: MessageVersion = "pain.001.001.03"
# shortcut: published as `maximum` on `transaction_count` until `transactions[]` exists; the Supplied Data ticket
# adds `maxItems: 100` to it.
MAX_TRANSACTIONS = 100
DEFAULT_TRANSACTION_COUNT = 10
MAX_SEED_LENGTH = 64
DEFAULT_COUNTRIES: tuple[SupportedCountry, ...] = ("GB", "DE", "FR", "NL", "US")
DEFAULT_AMOUNT_MIN = Decimal("10.00")
DEFAULT_AMOUNT_MAX = Decimal("50000.00")


def _iso_4217(code: str) -> str:
    if pycountry.currencies.get(alpha_3=code) is None:
        msg = f"{code!r} is not an ISO 4217 currency code"
        raise ValueError(msg)
    return code


type CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$"), AfterValidator(_iso_4217)]
type Amount = Annotated[Decimal, Field(gt=0, max_digits=17, decimal_places=2)]
# Plain aliases, not `type`, so the OpenAPI document inlines them rather than naming a schema for each.
Seed = Annotated[str, Field(min_length=1, max_length=MAX_SEED_LENGTH)]
MessageId = Annotated[str, Field(min_length=1, max_length=35)]
TransactionCount = Annotated[int, Field(ge=1, le=MAX_TRANSACTIONS)]


class GenerationRequest(BaseModel):
    """What a caller asks for, every field optional. `EffectiveRequest` is the same with every default resolved."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    message_version: MessageVersion = DEFAULT_MESSAGE_VERSION
    seed: Seed | None = Field(
        default=None, description="Any string; absent means 16 hex characters from the OS random source"
    )
    created_at: datetime | None = Field(default=None, description="`GrpHdr/CreDtTm`; absent means now")
    execution_date: date | None = Field(default=None, description="`ReqdExctnDt`; absent means today")
    message_id: MessageId | None = Field(default=None, description="`GrpHdr/MsgId`; absent means drawn from the Seed")
    transaction_count: TransactionCount | None = Field(
        default=None, description=f"Absent means {DEFAULT_TRANSACTION_COUNT}"
    )
    hit_count: int = Field(
        default=0, ge=0, description="Sanctioned Entities placed as drawn Hits; at most the transaction count plus two"
    )
    countries: list[SupportedCountry] = Field(
        default=list(DEFAULT_COUNTRIES),
        min_length=1,
        description="The Debtor takes the first; creditors and their agents draw from all of them",
    )
    currencies: list[CurrencyCode] | None = Field(
        default=None, min_length=1, description="Each transaction draws one; absent means the creditor country's"
    )
    amount_min: Amount = DEFAULT_AMOUNT_MIN
    amount_max: Amount = DEFAULT_AMOUNT_MAX
    exposure_countries: list[ExposureCountry] = Field(
        default=list(EXPOSURE_COUNTRIES), min_length=1, description="Each Exposure draws its country from them"
    )
    exposure_count: int = Field(
        default=0,
        ge=0,
        description="Clean transactions with the creditor side in an exposure country, none of them carrying a Hit",
    )

    @field_validator("amount_max")
    @classmethod
    def _range(cls, amount_max: Decimal, info: ValidationInfo) -> Decimal:
        amount_min = info.data.get("amount_min")
        if amount_min is not None and amount_max < amount_min:
            msg = "amount_max must not be below amount_min"
            raise ValueError(msg)
        return amount_max

    @field_validator("hit_count")
    @classmethod
    def _hit_cap(cls, hit_count: int, info: ValidationInfo) -> int:
        """Two file-level Placements (Debtor, Debtor Agent) plus one Hit per transaction (spec 6.3)."""
        if "transaction_count" not in info.data:
            return hit_count  # transaction_count failed its own validation
        cap = (info.data["transaction_count"] or DEFAULT_TRANSACTION_COUNT) + 2
        if hit_count > cap:
            msg = f"hit_count must not exceed the transaction count plus two ({cap})"
            raise ValueError(msg)
        return hit_count

    @field_validator("exposure_count")
    @classmethod
    def _exposure_cap(cls, exposure_count: int, info: ValidationInfo) -> int:
        """Exposures take transactions no Hit touches; Hits beyond the two file-level ones take one each (spec 8.2)."""
        if "transaction_count" not in info.data or "hit_count" not in info.data:
            return exposure_count  # validated on their own
        transaction_count = info.data["transaction_count"] or DEFAULT_TRANSACTION_COUNT
        cap = transaction_count - max(0, info.data["hit_count"] - 2)
        if exposure_count > cap:
            msg = f"exposure_count must not exceed the transactions left free of Hits ({cap})"
            raise ValueError(msg)
        return exposure_count

    def resolve(self) -> "EffectiveRequest":
        """Resolve every default (spec 5.7). Replaying the result reproduces the Sample File byte for byte."""
        seed = self.seed or secrets.token_hex(8)
        now = datetime.now(UTC).replace(microsecond=0)
        return EffectiveRequest.model_validate(
            {
                **self.model_dump(),
                "seed": seed,
                "created_at": self.created_at or now,
                "execution_date": self.execution_date or now.date(),
                "message_id": self.message_id or identifier("MSG", stream(seed, "file/message_id")),
                "transaction_count": self.transaction_count or DEFAULT_TRANSACTION_COUNT,
            }
        )


class EffectiveRequest(GenerationRequest):
    """The request with every default resolved, as embedded in the Answer Key."""

    seed: Seed
    created_at: datetime
    execution_date: date
    message_id: MessageId
    transaction_count: TransactionCount
