"""Supplied Data (spec 5.1, 5.3, 5.4): the `payment` and `transactions[]` parts of a request, and their merge.

Every field is three-state: absent (`MISSING`) is generated from the Seed, an explicit `null` leaves an optional
element out, and a value is used as given. A field whose element is required has no `null` in its type, so a `null`
there fails validation like any other wrong type.
"""

import re
from collections.abc import Iterator
from decimal import Decimal
from typing import Annotated, Self

import pycountry
from pydantic import MISSING, AfterValidator, BaseModel, ConfigDict, Field, model_validator
from pydantic_core import InitErrorDetails, PydanticCustomError
from schwifty import IBAN
from schwifty.exceptions import SchwiftyException

DEC2014_BIC = r"^[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$"
"""`BICFIDec2014Identifier`, from .09; the field's own pattern, the looser of the two."""
STRICT_BIC = r"^[A-Z]{6}[A-Z2-9][A-NP-Z0-9]([A-Z0-9]{3})?$"
"""`BICIdentifier` and `BICFIIdentifier`, .03 to .08."""
FIRST_WITH_LEI = 9
FIRST_WITH_POSTAL_ADDRESS_24 = 9
FIRST_WITH_POSTAL_ADDRESS_27 = 12
NARROW_BEFORE_27 = {"street": 70, "town": 35, "building_name": 35, "town_location_name": 35, "district_name": 35}
"""PostalAddress6 and 24 limits that PostalAddress27 widens to 140. The spec says 70 for town; the XSD says 35."""
POSTAL_ADDRESS_24_PARTS = ("building_name", "floor", "post_box", "room", "town_location_name", "district_name")
POSTAL_ADDRESS_27_PARTS = ("care_of", "unit_number")
MAX_INTERMEDIARY_AGENTS = 3


def _iso_3166(code: str) -> str:
    if pycountry.countries.get(alpha_2=code) is None:
        msg = f"{code!r} is not an ISO 3166 country code"
        raise ValueError(msg)
    return code


def _iso_4217(code: str) -> str:
    if pycountry.currencies.get(alpha_3=code) is None:
        msg = f"{code!r} is not an ISO 4217 currency code"
        raise ValueError(msg)
    return code


def _iban(value: str) -> str:
    try:
        return IBAN(value).compact
    except SchwiftyException as error:
        msg = f"IBAN is not valid: {error}"
        raise ValueError(msg) from error


def _bic(value: str) -> str:
    _iso_3166(value[4:6])
    return value


# Plain aliases, not `type`, so the OpenAPI document inlines them rather than naming a schema for each.
Country = Annotated[str, Field(pattern=r"^[A-Z]{2}$"), AfterValidator(_iso_3166)]
CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$"), AfterValidator(_iso_4217)]
Amount = Annotated[Decimal, Field(gt=0, max_digits=17, decimal_places=2)]
Bic = Annotated[str, Field(pattern=DEC2014_BIC), AfterValidator(_bic)]
Lei = Annotated[str, Field(pattern=r"^[A-Z0-9]{18}[0-9]{2}$")]
Text4 = Annotated[str, Field(min_length=1, max_length=4)]
Text16 = Annotated[str, Field(min_length=1, max_length=16)]
Text34 = Annotated[str, Field(min_length=1, max_length=34)]
Text35 = Annotated[str, Field(min_length=1, max_length=35)]
Text70 = Annotated[str, Field(min_length=1, max_length=70)]
Text140 = Annotated[str, Field(min_length=1, max_length=140)]
"""`Max140Text`: every party and agent `Nm`."""

_FORBID = ConfigDict(extra="forbid", frozen=True)


class SuppliedAddress(BaseModel):
    """`PstlAdr`. Widths are the widest any Message Version allows; narrower versions are checked per request."""

    model_config = _FORBID

    care_of: Text140 | MISSING | None = Field(default=MISSING, description="From .12")
    street: Text140 | MISSING | None = Field(default=MISSING, description="70 characters before .12")
    building_number: Text16 | MISSING | None = MISSING
    building_name: Text140 | MISSING | None = Field(default=MISSING, description="From .09; 35 characters before .12")
    floor: Text70 | MISSING | None = Field(default=MISSING, description="From .09")
    unit_number: Text16 | MISSING | None = Field(default=MISSING, description="From .12")
    post_box: Text16 | MISSING | None = Field(default=MISSING, description="From .09")
    room: Text70 | MISSING | None = Field(default=MISSING, description="From .09")
    postcode: Text16 | MISSING | None = MISSING
    town: Text140 | MISSING | None = Field(default=MISSING, description="35 characters before .12")
    town_location_name: Text140 | MISSING | None = Field(
        default=MISSING, description="From .09; 35 characters before .12"
    )
    district_name: Text140 | MISSING | None = Field(default=MISSING, description="From .09; 35 characters before .12")
    country_subdivision: Text35 | MISSING | None = MISSING
    country: Country | MISSING | None = Field(default=MISSING, description="Any ISO 3166 country")
    lines: list[Text70] | MISSING | None = Field(
        default=MISSING, max_length=7, description="`AdrLine`: an unstructured address, with `country` only"
    )

    @model_validator(mode="after")
    def _lines_alone(self) -> Self:
        structured = self.model_fields_set - {"lines", "country"}
        if self.lines not in (None, MISSING) and structured:
            msg = f"lines replace the structured parts; supply one or the other, not {', '.join(sorted(structured))}"
            raise ValueError(msg)
        return self


class SuppliedPartyId(BaseModel):
    """`Id/OrgId/Othr`."""

    model_config = _FORBID

    other_id: Text35
    scheme: Text4 | None = Field(default=None, description="`SchmeNm/Cd`, e.g. `TXID`")


class SuppliedParty(BaseModel):
    model_config = _FORBID

    name: Text140 | MISSING = MISSING
    address: SuppliedAddress | MISSING | None = MISSING
    id: SuppliedPartyId | MISSING | None = MISSING
    country_of_residence: Country | MISSING | None = MISSING


class SuppliedAgent(BaseModel):
    model_config = _FORBID

    bic: Bic | MISSING | None = Field(default=MISSING, description="Strict `BICIdentifier` pattern before .09")
    lei: Lei | MISSING | None = Field(default=MISSING, description="From .09")
    name: Text140 | MISSING | None = MISSING
    address: SuppliedAddress | MISSING | None = MISSING

    @model_validator(mode="after")
    def _identified(self) -> Self:
        if self.bic is None and self.name is None:
            msg = "an agent needs a BIC or a name; both are null"
            raise ValueError(msg)
        return self


class SuppliedAccount(BaseModel):
    """Either `iban`, or `other_id` with an optional `scheme`."""

    model_config = _FORBID

    iban: Annotated[str, AfterValidator(_iban)] | MISSING = Field(default=MISSING, description="Checksum-validated")
    other_id: Text34 | MISSING = Field(default=MISSING, description="`Othr/Id`")
    scheme: Text4 | MISSING = Field(default=MISSING, description="`Othr/SchmeNm/Cd`, e.g. `BBAN`")

    @model_validator(mode="after")
    def _one_identifier(self) -> Self:
        if (self.iban is MISSING) == (self.other_id is MISSING):
            msg = "an account is either an iban or an other_id"
            raise ValueError(msg)
        if self.iban is not MISSING and self.scheme is not MISSING:
            msg = "scheme goes with other_id, not iban"
            raise ValueError(msg)
        return self


class SuppliedStructuredRemittance(BaseModel):
    """`Strd`."""

    model_config = _FORBID

    creditor_reference: Text35 | MISSING | None = MISSING
    invoicer: Text140 | MISSING | None = Field(default=MISSING, description="`Invcr/Nm`")
    invoicee: Text140 | MISSING | None = Field(default=MISSING, description="`Invcee/Nm`")
    additional: list[Text140] | MISSING | None = Field(default=MISSING, max_length=3, description="`AddtlRmtInf`")


class SuppliedRemittance(BaseModel):
    model_config = _FORBID

    unstructured: list[Text140] | MISSING | None = Field(default=MISSING, description="`Ustrd`, one per line")
    structured: SuppliedStructuredRemittance | MISSING | None = MISSING


class SuppliedPayment(BaseModel):
    """File-level Supplied Data: the one Debtor, Debtor Agent and Debtor account (spec 6.2)."""

    model_config = _FORBID

    payment_information_id: Text35 | MISSING = MISSING
    debtor: SuppliedParty | MISSING = Field(
        default=MISSING, description="A supplied address country overrides `countries[0]` as the Debtor's"
    )
    debtor_agent: SuppliedAgent | MISSING = MISSING
    debtor_account: SuppliedAccount | MISSING = MISSING


class SuppliedTransaction(BaseModel):
    model_config = _FORBID

    end_to_end_id: Text35 | MISSING = MISSING
    creditor: SuppliedParty | MISSING = MISSING
    creditor_agent: SuppliedAgent | MISSING = MISSING
    creditor_account: SuppliedAccount | MISSING = MISSING
    amount: Amount | MISSING = MISSING
    currency: CurrencyCode | MISSING = MISSING
    ultimate_debtor: SuppliedParty | MISSING | None = MISSING
    ultimate_creditor: SuppliedParty | MISSING | None = MISSING
    intermediary_agents: list[SuppliedAgent] | MISSING | None = Field(
        default=MISSING, max_length=MAX_INTERMEDIARY_AGENTS, description="`IntrmyAgt1` to `IntrmyAgt3`, in order"
    )
    remittance: SuppliedRemittance | MISSING = MISSING


type Location = tuple[str | int, ...]


def field_error(location: Location, value: object, message: str) -> InitErrorDetails:
    """A `value_error` at `location`, for a check that spans fields but belongs to one of them."""
    return InitErrorDetails(
        type=PydanticCustomError("value_error", "{message}", {"message": message}), loc=location, input=value
    )


def roles(
    payment: SuppliedPayment | None, transactions: list[SuppliedTransaction]
) -> Iterator[tuple[Location, SuppliedParty | SuppliedAgent]]:
    """Every supplied party and agent with its location in the request."""
    if payment is not None:
        for name in ("debtor", "debtor_agent"):
            if (role := getattr(payment, name)) is not MISSING:
                yield ("payment", name), role
    for index, tx in enumerate(transactions):
        for name in ("creditor", "creditor_agent", "ultimate_debtor", "ultimate_creditor"):
            if isinstance(role := getattr(tx, name), SuppliedParty | SuppliedAgent):
                yield ("transactions", index, name), role
        for slot, agent in enumerate(tx.intermediary_agents if isinstance(tx.intermediary_agents, list) else ()):
            yield ("transactions", index, "intermediary_agents", slot), agent


def version_errors(
    message_version: str, payment: SuppliedPayment | None, transactions: list[SuppliedTransaction]
) -> list[InitErrorDetails]:
    """What the chosen Message Version cannot carry (spec 5.4). Supplied values are never dropped, so they fail here."""
    number = int(message_version.rsplit(".", 1)[1])
    errors: list[InitErrorDetails] = []

    def error(location: Location, value: object, message: str) -> None:
        errors.append(field_error(location, value, message))

    for location, role in roles(payment, transactions):
        if isinstance(role, SuppliedAgent):
            if isinstance(role.bic, str) and number < FIRST_WITH_LEI and not re.fullmatch(STRICT_BIC, role.bic):
                error(
                    (*location, "bic"), role.bic, f"BIC does not match the BICIdentifier pattern of {message_version}"
                )
            if isinstance(role.lei, str) and number < FIRST_WITH_LEI:
                error((*location, "lei"), role.lei, f"an agent LEI is not in {message_version}; it exists from .09")
        if not isinstance(role.address, SuppliedAddress):
            continue
        address = role.address
        for part in POSTAL_ADDRESS_24_PARTS:
            if getattr(address, part) is not MISSING and number < FIRST_WITH_POSTAL_ADDRESS_24:
                error(
                    (*location, "address", part),
                    getattr(address, part),
                    f"{part} is not in {message_version}; it exists from .09",
                )
        for part in POSTAL_ADDRESS_27_PARTS:
            value = getattr(address, part)
            if value is MISSING:
                continue
            if number < FIRST_WITH_POSTAL_ADDRESS_27:
                error((*location, "address", part), value, f"{part} is not in {message_version}; it exists from .12")
            elif value is not None:
                # shortcut: pain001's corpus.build has no key for CareOf or UnitNb and `raw` merges are not used
                # (spec 10.2); supporting them needs a pain001 release that emits them, or a ticket for `raw`.
                error((*location, "address", part), value, f"{part} is not supported yet")
        if number < FIRST_WITH_POSTAL_ADDRESS_27:
            for part, limit in NARROW_BEFORE_27.items():
                value = getattr(address, part)
                if isinstance(value, str) and len(value) > limit:
                    error(
                        (*location, "address", part),
                        value,
                        f"{part} is over {limit} characters, the limit in {message_version}",
                    )
    return errors
