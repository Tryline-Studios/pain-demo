"""Generated Data (spec 4.4, 4.5, 5.3, 5.5): every party, agent, account and amount drawn from the Seed.

Banks and BICs come only from the Clean Bank List; schwifty only assembles IBANs around them. Faker draws names and
addresses, one instance per country, re-seeded with `seed_instance()` from the stream of the role it draws for, and
every name it draws is screened against the Entity Catalogue and redrawn from the same stream on a match.
"""

import random
import string
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import cast

from faker import Faker
from schwifty import IBAN

from pain_demo.generation.clean_banks import IBAN_COUNTRIES, CleanBank, CleanBankList, SupportedCountry
from pain_demo.generation.model import (
    Account,
    Address,
    Agent,
    Iban,
    OtherAccount,
    Party,
    Remittance,
    SampleFileModel,
    Transaction,
)
from pain_demo.generation.request import CurrencyCode, EffectiveRequest
from pain_demo.generation.screening import NameScreen
from pain_demo.generation.seeds import identifier, stream

ULTIMATE_CREDITOR_RATE = 0.10
ULTIMATE_DEBTOR_RATE = 0.05
INTERMEDIARY_AGENT_RATE = 0.05
STRUCTURED_REMITTANCE_RATE = 0.15
"""Background rates of the optional roles in clean transactions (spec 5.3)."""

MAX_TOWN_LENGTH = 35
"""`TwnNm` is Max35Text before .12; some Faker locales draw longer towns."""


@dataclass(frozen=True)
class CountryProfile:
    locale: str
    """The Faker locale that draws this country's names and addresses."""
    currency: CurrencyCode
    """A creditor's currency when the request names no `currencies` (spec 5.5)."""
    account_digits: int | None
    """Digits we draw for an account: the IBAN's account code, or the whole US account number. None for DE: its check
    digit sits in the account code, so schwifty draws it."""
    iban: bool = True
    """False for US: `Othr/Id` with the account number, the routing number on the agent (spec 4.5)."""


COUNTRIES: dict[SupportedCountry, CountryProfile] = {
    "GB": CountryProfile("en_GB", "GBP", 8),
    "IE": CountryProfile("en_IE", "EUR", 8),
    "DE": CountryProfile("de_DE", "EUR", None),
    "FR": CountryProfile("fr_FR", "EUR", 11),
    "IT": CountryProfile("it_IT", "EUR", 12),
    "ES": CountryProfile("es_ES", "EUR", 10),
    "NL": CountryProfile("nl_NL", "EUR", 10),
    "BE": CountryProfile("nl_BE", "EUR", 7),
    "PL": CountryProfile("pl_PL", "PLN", 16),
    "AT": CountryProfile("de_AT", "EUR", 11),
    "PT": CountryProfile("pt_PT", "EUR", 11),
    "US": CountryProfile("en_US", "USD", 10, iban=False),
}
MAX_REDRAWS = 1000
ACCOUNT_IBAN_COUNTRIES = frozenset({"BY", "IR", *IBAN_COUNTRIES})
"""Where an account is an IBAN (spec 6.9); everywhere else it is `Othr/Id`."""

REMITTANCE_TEMPLATES = ("Invoice {n}", "Order {n}", "Contract {n} instalment", "Services rendered, ref {n}")


class GeneratedData:
    """Draws one Sample File's Generated Data for an Effective Request."""

    def __init__(self, request: EffectiveRequest, clean_banks: CleanBankList, screen: NameScreen) -> None:
        self.request = request
        self.clean_banks = clean_banks
        self.screen = screen
        self._fakers: dict[SupportedCountry, Faker] = {}

    def sample_file_model(self) -> SampleFileModel:
        request = self.request
        debtor_country = request.countries[0]
        debtor_agent, debtor_account = self._bank_and_account(self._stream("file/debtor_agent"), debtor_country)
        return SampleFileModel(
            message_version=request.message_version,
            message_id=request.message_id,
            created_at=request.created_at,
            execution_date=request.execution_date,
            payment_information_id=identifier("PMT", self._stream("file/identifiers")),
            debtor=self._party(self._stream("file/debtor"), debtor_country, company=True),
            debtor_account=debtor_account,
            debtor_agent=debtor_agent,
            transactions=tuple(self._transaction(number) for number in range(1, request.transaction_count + 1)),
        )

    def _transaction(self, number: int) -> Transaction:
        def tx_stream(name: str) -> random.Random:
            return self._stream(f"tx/{number}/{name}")

        request = self.request
        country = tx_stream("country").choice(request.countries)
        creditor_stream = tx_stream("creditor")
        creditor_agent, creditor_account = self._bank_and_account(tx_stream("creditor_agent"), country)
        amount_stream = tx_stream("amount")
        currency = amount_stream.choice(request.currencies) if request.currencies else COUNTRIES[country].currency
        cents = amount_stream.randint(int(request.amount_min * 100), int(request.amount_max * 100))
        # Always four draws, in this order, so one role's odds never depend on another's.
        optional = tx_stream("optional")
        ultimate_creditor, ultimate_debtor, intermediary, structured = (
            optional.random() < rate
            for rate in (
                ULTIMATE_CREDITOR_RATE,
                ULTIMATE_DEBTOR_RATE,
                INTERMEDIARY_AGENT_RATE,
                STRUCTURED_REMITTANCE_RATE,
            )
        )
        intermediary_stream = tx_stream("intermediary_agent")
        return Transaction(
            end_to_end_id=identifier("E2E", tx_stream("identifiers")),
            amount=Decimal(cents).scaleb(-2),
            currency=currency,
            creditor=self._party(creditor_stream, country, company=creditor_stream.random() < 0.5),
            creditor_agent=creditor_agent,
            creditor_account=creditor_account,
            remittance=_remittance(tx_stream("remittance"), structured=structured),
            ultimate_debtor=(
                self._party(tx_stream("ultimate_debtor"), request.countries[0], with_address=False)
                if ultimate_debtor
                else None
            ),
            ultimate_creditor=(
                self._party(tx_stream("ultimate_creditor"), country, with_address=False) if ultimate_creditor else None
            ),
            intermediary_agents=(
                (self.clean_agent(intermediary_stream, intermediary_stream.choice(request.countries))[0],)
                if intermediary
                else ()
            ),
        )

    def _stream(self, name: str) -> random.Random:
        return stream(self.request.seed, name)

    def _faker(self, rng: random.Random, country: SupportedCountry) -> Faker:
        faker = self._fakers.get(country) or self._fakers.setdefault(country, Faker(COUNTRIES[country].locale))
        faker.seed_instance(rng.getrandbits(64))
        return faker

    def _party(
        self, rng: random.Random, country: SupportedCountry, *, company: bool = False, with_address: bool = True
    ) -> Party:
        faker = self._faker(rng, country)
        draw = faker.company if company else faker.name
        name = _redraw(draw, self.screen.matches)
        if not with_address:
            return Party(name=name)
        return Party(
            name=name,
            address=Address(
                street=faker.street_name(),
                building_number=faker.building_number(),
                post_code=faker.postcode(),
                town=_redraw(faker.city, lambda town: len(town) > MAX_TOWN_LENGTH),
                country=country,
            ),
        )

    def clean_agent(self, rng: random.Random, country: SupportedCountry) -> tuple[Agent, CleanBank]:
        bank = rng.choice(self.clean_banks.for_country(country))
        return Agent(bic=bank.bic, name=bank.name, routing_number=bank.routing_number), bank

    def _bank_and_account(self, rng: random.Random, country: SupportedCountry) -> tuple[Agent, Account]:
        agent, bank = self.clean_agent(rng, country)
        return agent, self.account(rng, country, bank.bank_code)

    def account(self, rng: random.Random, country: str, bank_code: str | None) -> Account:
        """A clean account in any `country` (spec 6.9): IBAN for BY, IR and the IBAN defaults, else `Othr/Id`.

        Without a `bank_code`, an IBAN in one of the twelve countries takes a Clean Bank List bank's code.
        """
        if country == "IR":
            # schwifty's IR spec has no bank or account positions and yields all zeros: BBAN 0 + bank + 18 digits.
            return Iban(_iban("IR", "0" + digits(rng, 21)))
        profile = COUNTRIES.get(country)  # one of the twelve clean countries, else None
        if country in ACCOUNT_IBAN_COUNTRIES:
            account_digits = profile.account_digits if profile else 16  # BY: 16 after the bank code and branch
            if bank_code is None and profile:
                bank_code = rng.choice(self.clean_banks.for_country(cast("SupportedCountry", country))).bank_code
            codes = {"bank_code": bank_code} if bank_code else {}
            if account_digits:
                codes["account_code"] = digits(rng, account_digits)
            return Iban(str(IBAN.random(country, random=rng, use_registry=False, **codes)))
        if country == "RU":
            return OtherAccount("40702810" + digits(rng, 12))  # 20 digits: balance account, currency, then the rest
        return OtherAccount(digits(rng, (profile.account_digits or 10) if profile else 16))


def _redraw(draw: Callable[[], str], refused: Callable[[str], bool]) -> str:
    """Draw until `refused` passes, consuming from the stream the first draw came from (spec 9.3)."""
    for _ in range(MAX_REDRAWS):
        value = draw()
        if not refused(value):
            return value
    msg = f"no acceptable value in {MAX_REDRAWS} draws"
    raise RuntimeError(msg)


def _iban(country: str, bban: str) -> str:
    numeric = int("".join(str(int(char, 36)) for char in bban + country + "00"))
    return f"{country}{98 - numeric % 97:02d}{bban}"


def digits(rng: random.Random, length: int) -> str:
    return "".join(rng.choices(string.digits, k=length))


def _remittance(rng: random.Random, *, structured: bool) -> Remittance:
    if structured:
        return Remittance(creditor_reference=creditor_reference(digits(rng, 12)))
    return Remittance(unstructured=rng.choice(REMITTANCE_TEMPLATES).format(n=digits(rng, 6)))


def creditor_reference(body: str) -> str:
    """An ISO 11649 `RF` reference around `body` (digits and capital letters)."""
    numeric = "".join(str(int(char, 36)) for char in f"{body}RF00")
    return f"RF{98 - int(numeric) % 97:02d}{body}"
