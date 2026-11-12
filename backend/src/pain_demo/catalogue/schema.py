"""The Entity Catalogue schema (spec section 3.3): one TOML file per Entity plus the Control Relationships file.

Every model forbids unknown fields, so anything the spec leaves out (weak aliases, ID documents, personal addresses)
cannot enter the catalogue by accident.
"""

from collections.abc import Iterable
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from pain_demo.identifiers import BIC_PATTERN, well_formed_bic

type EntityType = Literal["individual", "bank", "corporate"]
type SanctionsList = Literal["ofac_sdn", "uk"]
type NameSourceType = Literal["primary", "primary_variation", "aka", "fka", "nka"]
type Script = Literal["latin", "cyrillic", "arabic", "han"]
type ScriptSource = Literal["stated", "derived"]
type ControlRole = Literal[
    "ultimate_beneficial_owner", "controlling_shareholder", "director", "officer", "parent_company"
]
type ControlStatus = Literal["current", "former", "as_listed"]

type EntityId = Annotated[str, Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
type CountryCode = Annotated[str, Field(pattern=r"^[A-Z]{2}$", description="ISO 3166-1 alpha-2")]
type LanguageCode = Annotated[str, Field(pattern=r"^[a-z]{2}$", description="ISO 639-1")]
type NonEmpty = Annotated[str, Field(min_length=1)]

_LEI_PATTERN = r"^[A-Z0-9]{18}[0-9]{2}$"


class CatalogueModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ListingRef(CatalogueModel):
    """Points at one of the Entity's own Listings: the source of a name, address, identifier or BIC."""

    list: SanctionsList
    entry_id: NonEmpty


class Verification(CatalogueModel):
    """The list snapshot a Listing was last checked against."""

    snapshot_date: date
    source_file: NonEmpty


class Listing(CatalogueModel):
    list: SanctionsList
    entry_id: NonEmpty
    programmes: list[NonEmpty] = Field(min_length=1, description="OFAC programme codes or the UK regime")
    designation_date: date
    verified: Verification

    @property
    def ref(self) -> ListingRef:
        return ListingRef(list=self.list, entry_id=self.entry_id)


class Name(CatalogueModel):
    value: NonEmpty
    source_type: NameSourceType
    script: Script
    script_source: ScriptSource
    language: LanguageCode | None = Field(default=None, description="Only when the list states it")
    listing: ListingRef


class Address(CatalogueModel):
    lines: list[NonEmpty] = Field(min_length=1)
    city: NonEmpty | None = None
    region: NonEmpty | None = None
    postal_code: NonEmpty | None = None
    country: CountryCode
    listing: ListingRef


class RegistrationNumber(CatalogueModel):
    value: NonEmpty
    type: NonEmpty = Field(description="The identifier type as the list names it, e.g. `Tax ID No.`")
    country: CountryCode | None = None
    listing: ListingRef


class Lei(CatalogueModel):
    value: str = Field(pattern=_LEI_PATTERN)
    source: NonEmpty = Field(description="How the GLEIF record was matched to the Entity, and when")
    gleif_legal_name: NonEmpty = Field(description="The legal name on the GLEIF record, which may have moved on")

    @field_validator("value")
    @classmethod
    def _check_digits(cls, value: str) -> str:
        if not lei_check_digits_hold(value):
            msg = "LEI check digits do not hold"
            raise ValueError(msg)
        return value


class Bic(CatalogueModel):
    """Either the Listing that carries the BIC or an external non-sanctions citation, never both."""

    value: str = Field(pattern=BIC_PATTERN)
    listing: ListingRef | None = None
    citation: NonEmpty | None = Field(default=None, description="e.g. the GLEIF BIC-to-LEI mapping file")
    verified_date: date

    _well_formed = field_validator("value")(well_formed_bic)

    @model_validator(mode="after")
    def _one_source(self) -> "Bic":
        if (self.listing is None) == (self.citation is None):
            msg = "a BIC names exactly one source: its Listing or an external citation"
            raise ValueError(msg)
        return self


class EntityBase(CatalogueModel):
    id: EntityId
    listings: list[Listing] = Field(min_length=1)
    names: list[Name] = Field(min_length=1)

    @model_validator(mode="after")
    def _names_have_a_primary_from_own_listings(self) -> "EntityBase":
        if not any(name.source_type == "primary" for name in self.names):
            msg = "an Entity needs a primary name"
            raise ValueError(msg)
        self._check_listing_refs(name.listing for name in self.names)
        return self

    def _check_listing_refs(self, refs: Iterable[ListingRef]) -> None:
        own = {listing.ref for listing in self.listings}
        for ref in refs:
            if ref not in own:
                msg = f"{ref.list} {ref.entry_id} is not one of this Entity's Listings"
                raise ValueError(msg)

    @property
    def display_name(self) -> str:
        return next(name.value for name in self.names if name.source_type == "primary")

    @property
    def lists(self) -> list[SanctionsList]:
        return sorted({listing.list for listing in self.listings})


class LegalEntityBase(EntityBase):
    addresses: list[Address] = []
    lei: Lei | None = None
    registration_numbers: list[RegistrationNumber] = []

    @model_validator(mode="after")
    def _legal_entity_refs(self) -> "LegalEntityBase":
        self._check_listing_refs(address.listing for address in self.addresses)
        self._check_listing_refs(number.listing for number in self.registration_numbers)
        return self

    @property
    def countries(self) -> list[CountryCode]:
        return list(dict.fromkeys(address.country for address in self.addresses))


class Bank(LegalEntityBase):
    entity_type: Literal["bank"]
    bics: list[Bic] = Field(default=[], description="May be empty: such a Bank is placed by name and address only")

    @model_validator(mode="after")
    def _bic_refs(self) -> "Bank":
        self._check_listing_refs(bic.listing for bic in self.bics if bic.listing is not None)
        return self


class Corporate(LegalEntityBase):
    entity_type: Literal["corporate"]


class Individual(EntityBase):
    entity_type: Literal["individual"]
    date_of_birth: date | None = None
    place_of_birth: NonEmpty | None = None
    nationalities: list[CountryCode] = []
    country_of_residence: CountryCode | None = Field(default=None, description="Only when a list states it")

    @property
    def countries(self) -> list[CountryCode]:
        stated = [*self.nationalities, *([self.country_of_residence] if self.country_of_residence else [])]
        return list(dict.fromkeys(stated))


type Entity = Annotated[Individual | Bank | Corporate, Field(discriminator="entity_type")]
type LegalEntity = Bank | Corporate


class ControlRelationship(CatalogueModel):
    controller: EntityId
    controlled: EntityId = Field(description="Always a Legal Entity")
    role: ControlRole
    status: ControlStatus
    as_of: date
    source: NonEmpty = Field(description="The Listing and the words it uses")


class ControlRelationshipsFile(CatalogueModel):
    relationships: list[ControlRelationship] = []


def lei_check_digits_hold(lei: str) -> bool:
    """ISO 7064 MOD 97-10 over the whole code, letters read as 10 to 35, must leave remainder 1."""
    digits = "".join(str(int(char, 36)) for char in lei)
    return int(digits) % 97 == 1
