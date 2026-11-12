"""The generation request (spec 5.1, 5.5, 12.4) and its Effective Request (spec 5.7).

Named Hits arrive with their own ticket.
"""

import secrets
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo, field_validator, model_validator

from pain_demo.generation.clean_banks import SupportedCountry
from pain_demo.generation.exposure_countries import EXPOSURE_COUNTRIES, ExposureCountry
from pain_demo.generation.seeds import identifier, stream
from pain_demo.generation.supplied import (
    Amount,
    CurrencyCode,
    SuppliedPayment,
    SuppliedTransaction,
    field_error,
    version_errors,
)

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
MAX_TRANSACTIONS = 100
DEFAULT_TRANSACTION_COUNT = 10
MAX_SEED_LENGTH = 64
DEFAULT_COUNTRIES: tuple[SupportedCountry, ...] = ("GB", "DE", "FR", "NL", "US")
DEFAULT_AMOUNT_MIN = Decimal("10.00")
DEFAULT_AMOUNT_MAX = Decimal("50000.00")

# Plain aliases, not `type`, so the OpenAPI document inlines them rather than naming a schema for each.
Seed = Annotated[str, Field(min_length=1, max_length=MAX_SEED_LENGTH)]
MessageId = Annotated[str, Field(min_length=1, max_length=35)]
TransactionCount = Annotated[int, Field(ge=1, le=MAX_TRANSACTIONS)]


def _absent(value: object) -> bool:
    return value is None


def _none_supplied(value: list[SuppliedTransaction]) -> bool:
    return not value


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
        default=None,
        description=f"Absent means the number of supplied transactions, or {DEFAULT_TRANSACTION_COUNT} with none",
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
    payment: SuppliedPayment | None = Field(
        default=None, exclude_if=_absent, description="File-level Supplied Data; absent means all generated"
    )
    transactions: list[SuppliedTransaction] = Field(
        default_factory=list,
        max_length=MAX_TRANSACTIONS,
        exclude_if=_none_supplied,
        description="Per-transaction Supplied Data, row n for transaction n; rows past the end are generated",
    )

    @field_validator("amount_max")
    @classmethod
    def _range(cls, amount_max: Decimal, info: ValidationInfo) -> Decimal:
        amount_min = info.data.get("amount_min")
        if amount_min is not None and amount_max < amount_min:
            msg = "amount_max must not be below amount_min"
            raise ValueError(msg)
        return amount_max

    @model_validator(mode="after")
    def _across_fields(self) -> Self:
        """Checks that span fields, each reported at the field it names."""
        errors = version_errors(self.message_version, self.payment, self.transactions)
        count = self.transaction_count or len(self.transactions) or DEFAULT_TRANSACTION_COUNT
        if count < len(self.transactions):
            errors.append(
                field_error(
                    ("transaction_count",),
                    count,
                    f"transaction_count must not be below the {len(self.transactions)} supplied transactions",
                )
            )
        # Two file-level Placements (Debtor, Debtor Agent) plus one Hit per transaction (spec 6.3).
        if self.hit_count > count + 2:
            errors.append(
                field_error(
                    ("hit_count",),
                    self.hit_count,
                    f"hit_count must not exceed the transaction count plus two ({count + 2})",
                )
            )
        # Exposures take transactions no Hit touches; Hits beyond the two file-level ones take one each (spec 8.2).
        exposure_cap = count - max(0, self.hit_count - 2)
        if self.hit_count <= count + 2 and self.exposure_count > exposure_cap:
            errors.append(
                field_error(
                    ("exposure_count",),
                    self.exposure_count,
                    f"exposure_count must not exceed the transactions left free of Hits ({exposure_cap})",
                )
            )
        if errors:
            raise ValidationError.from_exception_data(type(self).__name__, errors)
        return self

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
                "transaction_count": self.transaction_count or len(self.transactions) or DEFAULT_TRANSACTION_COUNT,
            }
        )


class EffectiveRequest(GenerationRequest):
    """The request with every default resolved, as embedded in the Answer Key."""

    seed: Seed
    created_at: datetime
    execution_date: date
    message_id: MessageId
    transaction_count: TransactionCount
