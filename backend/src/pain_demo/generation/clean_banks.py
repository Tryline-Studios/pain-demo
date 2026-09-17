"""The Clean Bank List (spec section 4): the real, non-sanctioned banks Generated Data draws agents and accounts from.

A committed TOML file beside this module holds one entry per bank: country, bank code, BIC and name, plus the ABA
routing number for US entries. `load_clean_banks` validates it at startup and asserts it shares no BIC and no
normalised name with the Entity Catalogue, so a Sanctioned Entity can never enter a clean Sample File by accident.

A *normalised name* is the name casefolded, with diacritics stripped and every run of non-alphanumerics collapsed to
one space. Two BICs match on their first eight characters (institution, country, location), so a branch BIC of a
catalogue Bank is caught too.
"""

import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from pain_demo.catalogue import Catalogue
from pain_demo.identifiers import BIC_PATTERN, bic8, bic_country, well_formed_bic
from pain_demo.validated_files import FileProblems, parse_toml

type IbanCountry = Literal["GB", "IE", "DE", "FR", "IT", "ES", "NL", "BE", "PL", "AT", "PT"]
type SupportedCountry = Literal["GB", "IE", "DE", "FR", "IT", "ES", "NL", "BE", "PL", "AT", "PT", "US"]

IBAN_COUNTRIES: tuple[IbanCountry, ...] = ("GB", "IE", "DE", "FR", "IT", "ES", "NL", "BE", "PL", "AT", "PT")
SUPPORTED_COUNTRIES: tuple[SupportedCountry, ...] = (*IBAN_COUNTRIES, "US")

DEFAULT_PATH = Path(__file__).parent / "clean_banks.toml"

type NonEmpty = Annotated[str, Field(min_length=1)]


class CleanBank(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    country: SupportedCountry
    bank_code: NonEmpty = Field(description="The national bank identifier: IBAN bank code, or ABA routing number")
    bic: str = Field(pattern=BIC_PATTERN)
    name: NonEmpty
    routing_number: str | None = Field(default=None, pattern=r"^[0-9]{9}$", description="US entries only")

    _well_formed_bic = field_validator("bic")(well_formed_bic)

    @field_validator("routing_number")
    @classmethod
    def _aba_check_digit(cls, value: str | None) -> str | None:
        if value is not None and not aba_check_digit_holds(value):
            msg = "ABA routing number check digit does not hold"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _consistent(self) -> "CleanBank":
        if bic_country(self.bic) != self.country:
            msg = f"BIC {self.bic} is not a {self.country} BIC"
            raise ValueError(msg)
        if self.country == "US":
            if self.routing_number is None:
                msg = "a US entry carries its ABA routing number"
                raise ValueError(msg)
            if self.bank_code != self.routing_number:
                msg = "a US entry's bank code is its ABA routing number"
                raise ValueError(msg)
        elif self.routing_number is not None:
            msg = "only US entries carry an ABA routing number"
            raise ValueError(msg)
        return self


class CleanBankListFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    banks: list[CleanBank] = Field(min_length=1)


class CleanBankListError(FileProblems):
    """The list on disk is not usable or overlaps the Entity Catalogue; `problems` lists every reason."""


class CleanBankList:
    """The validated Clean Bank List, by country in file order."""

    def __init__(self, banks: Iterable[CleanBank]) -> None:
        self.banks = list(banks)
        self._by_country: dict[SupportedCountry, list[CleanBank]] = {country: [] for country in SUPPORTED_COUNTRIES}
        for bank in self.banks:
            self._by_country[bank.country].append(bank)

    def for_country(self, country: SupportedCountry) -> list[CleanBank]:
        return self._by_country[country]

    def __len__(self) -> int:
        return len(self.banks)


class CatalogueIndex:
    """What the Entity Catalogue is matched on: each Bank's BIC8s and every Entity's normalised names, to its id."""

    def __init__(self, catalogue: Catalogue) -> None:
        self.bic8s: dict[str, str] = {}
        self.names: dict[str, str] = {}
        self.bank_name_words: list[list[str]] = []
        for entity in catalogue.entities.values():
            for name in entity.names:
                if normalised := normalise_name(name.value):
                    self.names.setdefault(normalised, entity.id)
                    if entity.entity_type == "bank" and name.script == "latin":
                        self.bank_name_words.append(normalised.split())
            if entity.entity_type == "bank":
                for bic in entity.bics:
                    self.bic8s.setdefault(bic8(bic.value), entity.id)


def load_clean_banks(catalogue: Catalogue, path: Path = DEFAULT_PATH) -> CleanBankList:
    """Parse and validate the list, then assert it shares nothing with the Entity Catalogue (spec 4.3)."""
    problems: list[str] = []
    banks: list[CleanBank] = []
    if path.is_file():
        parsed = parse_toml(path, CleanBankListFile.model_validate, problems)
        banks = parsed.banks if parsed else []
    else:
        problems.append(f"{path.name}: missing")
    problems.extend(overlaps(banks, CatalogueIndex(catalogue)))
    if problems:
        raise CleanBankListError(problems)
    return CleanBankList(banks)


def overlaps(banks: Iterable[CleanBank], index: CatalogueIndex) -> list[str]:
    """Every Clean Bank List entry that shares a BIC or a normalised name with a catalogue Entity."""
    found: list[str] = []
    for bank in banks:
        if (entity_id := index.bic8s.get(bic8(bank.bic))) is not None:
            found.append(f"{bank.country} {bank.bic} {bank.name!r} shares a BIC with catalogue Entity {entity_id!r}")
        if (entity_id := index.names.get(normalise_name(bank.name))) is not None:
            found.append(f"{bank.country} {bank.bic} {bank.name!r} shares a name with catalogue Entity {entity_id!r}")
    return found


def normalise_name(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^0-9a-z]+", " ", stripped.casefold()).split())


def aba_check_digit_holds(routing_number: str) -> bool:
    """The ABA weights 3, 7, 1 over the nine digits sum to a multiple of ten."""
    digits = [int(char) for char in routing_number]
    weighted = 3 * (digits[0] + digits[3] + digits[6]) + 7 * (digits[1] + digits[4] + digits[7])
    return (weighted + digits[2] + digits[5] + digits[8]) % 10 == 0
