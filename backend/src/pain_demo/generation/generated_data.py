"""Generated Data (spec 4.4, 4.5, 5.3, 5.5): every party, agent, account and amount drawn from the Seed, with the
request's Supplied Data merged over it field by field.

Banks and BICs come only from the Clean Bank List; schwifty only assembles IBANs around them. Faker draws names and
addresses, one instance per country, re-seeded with `seed_instance()` from the stream of the role it draws for, and
every name it draws is screened against the Entity Catalogue and redrawn from the same stream on a match.
"""

import random
import string
from collections.abc import Callable
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import cast

from faker import Faker
from pydantic import MISSING
from schwifty import IBAN

from pain_demo.catalogue.transliteration import transliterate
from pain_demo.generation.clean_banks import IBAN_COUNTRIES, CleanBank, CleanBankList, SupportedCountry
from pain_demo.generation.exposure_countries import EXPOSURE_COUNTRIES, ExposureCountry
from pain_demo.generation.model import (
    Account,
    Address,
    Agent,
    Iban,
    ListedAddress,
    OtherAccount,
    Party,
    PartyId,
    Remittance,
    SampleFileModel,
    Transaction,
)
from pain_demo.generation.request import CurrencyCode, EffectiveRequest
from pain_demo.generation.screening import NameScreen
from pain_demo.generation.seeds import identifier, stream
from pain_demo.generation.supplied import (
    POSTAL_ADDRESS_27_PARTS,
    SuppliedAccount,
    SuppliedAddress,
    SuppliedAgent,
    SuppliedParty,
    SuppliedPayment,
    SuppliedRemittance,
    SuppliedTransaction,
)

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

EXPOSURE_BANK_NAMES = (
    "{city} Commercial Bank",
    "{city} Savings Bank",
    "{city} Trade and Credit Bank",
    "First {city} Bank",
    "{city} Cooperative Bank",
)
"""A synthetic Exposure agent's name around one of its country's cities (spec 8.3)."""
ROMANISED_COUNTRIES = frozenset({"RU", "BY"})
"""Exposure countries whose names are Faker `ru_RU` romanised under BGN/PCGN; the rest take the request's locales."""

REMITTANCE_TEMPLATES = ("Invoice {n}", "Order {n}", "Contract {n} instalment", "Services rendered, ref {n}")


class GeneratedData:
    """Draws one Sample File's Generated Data for an Effective Request."""

    def __init__(self, request: EffectiveRequest, clean_banks: CleanBankList, screen: NameScreen) -> None:
        self.request = request
        self.clean_banks = clean_banks
        self.screen = screen
        self._fakers: dict[str, Faker] = {}

    def sample_file_model(self) -> SampleFileModel:
        request = self.request
        payment = request.payment or SuppliedPayment()
        debtor_country = _debtor_country(payment) or request.countries[0]
        debtor_agent, debtor_account = self._bank_and_account(self._stream("file/debtor_agent"), debtor_country)
        rows = request.transactions
        return SampleFileModel(
            message_version=request.message_version,
            message_id=request.message_id,
            created_at=request.created_at,
            execution_date=request.execution_date,
            payment_information_id=pick(
                payment.payment_information_id, identifier("PMT", self._stream("file/identifiers"))
            ),
            debtor=merge_party(self._party(self._stream("file/debtor"), debtor_country, company=True), payment.debtor),
            debtor_account=merge_account(debtor_account, payment.debtor_account),
            debtor_agent=merge_agent(debtor_agent, payment.debtor_agent),
            transactions=tuple(
                self._transaction(
                    number, rows[number - 1] if number <= len(rows) else SuppliedTransaction(), debtor_country
                )
                for number in range(1, request.transaction_count + 1)
            ),
        )

    def _transaction(self, number: int, supplied: SuppliedTransaction, debtor_country: SupportedCountry) -> Transaction:
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

        def intermediary_agent(slot: int) -> Agent:
            rng = tx_stream("intermediary_agent" if slot == 1 else f"intermediary_agent_{slot}")
            return self.clean_agent(rng, rng.choice(request.countries))[0]

        # A supplied optional role is drawn whatever the background rate, so its gaps can be filled.
        ultimate_debtor_party = (
            self._party(tx_stream("ultimate_debtor"), debtor_country, with_address=False)
            if ultimate_debtor or isinstance(supplied.ultimate_debtor, SuppliedParty)
            else None
        )
        ultimate_creditor_party = (
            self._party(tx_stream("ultimate_creditor"), country, with_address=False)
            if ultimate_creditor or isinstance(supplied.ultimate_creditor, SuppliedParty)
            else None
        )
        generated_intermediaries = (intermediary_agent(1),) if intermediary else ()
        supplied_intermediaries = supplied.intermediary_agents
        return Transaction(
            end_to_end_id=pick(supplied.end_to_end_id, identifier("E2E", tx_stream("identifiers"))),
            amount=pick(supplied.amount, Decimal(cents).scaleb(-2)),
            currency=pick(supplied.currency, currency),
            creditor=merge_party(
                self._party(creditor_stream, country, company=creditor_stream.random() < 0.5), supplied.creditor
            ),
            creditor_agent=merge_agent(creditor_agent, supplied.creditor_agent),
            creditor_account=merge_account(creditor_account, supplied.creditor_account),
            remittance=merge_remittance(
                _remittance(tx_stream("remittance"), structured=structured), supplied.remittance
            ),
            ultimate_debtor=_optional_party(ultimate_debtor_party, supplied.ultimate_debtor),
            ultimate_creditor=_optional_party(ultimate_creditor_party, supplied.ultimate_creditor),
            intermediary_agents=(
                generated_intermediaries
                if supplied_intermediaries is MISSING
                else tuple(
                    merge_agent(intermediary_agent(slot), agent)
                    for slot, agent in enumerate(supplied_intermediaries or (), start=1)
                )
            ),  # ty: ignore[invalid-argument-type] - at most three, by the request's `max_length`
        )

    def _stream(self, name: str) -> random.Random:
        return stream(self.request.seed, name)

    def _faker(self, rng: random.Random, locale: str) -> Faker:
        faker = self._fakers.get(locale) or self._fakers.setdefault(locale, Faker(locale))
        faker.seed_instance(rng.getrandbits(64))
        return faker

    def _party(
        self, rng: random.Random, country: SupportedCountry, *, company: bool = False, with_address: bool = True
    ) -> Party:
        faker = self._faker(rng, COUNTRIES[country].locale)
        draw = faker.company if company else faker.name
        name = _redraw(draw, self.screen.matches)
        if not with_address:
            return Party(name=name)
        return Party(
            name=name,
            address=Address(
                street=faker.street_name(),
                building_number=faker.building_number(),
                postcode=faker.postcode(),
                town=_redraw(faker.city, lambda town: len(town) > MAX_TOWN_LENGTH),
                country=country,
            ),
        )

    def exposed_party(self, rng: random.Random, country: ExposureCountry) -> Party:
        """A Latin-script name, screened like every generated name, at a curated city (spec 8.3, 8.4)."""
        company = rng.random() < 0.5
        if country in ROMANISED_COUNTRIES:
            faker = self._faker(rng, "ru_RU")
            draw = faker.company if company else faker.name

            def romanised() -> str:
                return transliterate(draw().replace("«", "").replace("»", ""), "bgn_pcgn")

            name = _redraw(romanised, self.screen.matches)
        else:  # a foreign party at a local address: Faker has no usable Latin names for these countries
            faker = self._faker(rng, COUNTRIES[rng.choice(self.request.countries)].locale)
            name = _redraw(faker.company if company else faker.name, self.screen.matches)
        return Party(name=name, address=Address(town=rng.choice(EXPOSURE_COUNTRIES[country].cities), country=country))

    def exposed_agent_and_account(self, rng: random.Random, country: ExposureCountry) -> tuple[Agent, Account]:
        """A synthetic agent with an ISO test BIC (`0` eighth) and the account it services (spec 8.3, 6.9)."""
        cities = EXPOSURE_COUNTRIES[country].cities
        name = _redraw(lambda: rng.choice(EXPOSURE_BANK_NAMES).format(city=rng.choice(cities)), self.screen.matches)
        bank = "".join(rng.choices(string.ascii_uppercase, k=4))
        bic = f"{bank}{country}{rng.choice(string.ascii_uppercase)}0"
        return Agent(bic=bic, name=name), self.account(rng, country, bank if country == "BY" else None)

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
    return Remittance(unstructured=(rng.choice(REMITTANCE_TEMPLATES).format(n=digits(rng, 6)),))


def creditor_reference(body: str) -> str:
    """An ISO 11649 `RF` reference around `body` (digits and capital letters)."""
    numeric = "".join(str(int(char, 36)) for char in f"{body}RF00")
    return f"RF{98 - int(numeric) % 97:02d}{body}"


def _debtor_country(payment: SuppliedPayment) -> SupportedCountry | None:
    """A supplied Debtor address country overrides `countries[0]` (spec 5.3) where we can generate for it."""
    debtor = payment.debtor
    if debtor is MISSING or not isinstance(debtor.address, SuppliedAddress):
        return None
    country = debtor.address.country
    return country if country in COUNTRIES else None


def _optional_party(generated: Party | None, supplied: SuppliedParty | MISSING | None) -> Party | None:
    if isinstance(supplied, SuppliedParty):
        assert generated is not None  # noqa: S101 - drawn whenever a party is supplied
        return merge_party(generated, supplied)
    return pick(supplied, generated)


def pick[T](value: T | MISSING, generated: T) -> T:
    """The supplied value, or the generated one where the field is absent."""
    return generated if value is MISSING else value


def merge_party(generated: Party, supplied: SuppliedParty | MISSING) -> Party:
    if supplied is MISSING:
        return generated
    party_id = supplied.id
    return Party(
        name=pick(supplied.name, generated.name),
        address=merge_address(generated.address, supplied.address),
        id=generated.id
        if party_id is MISSING
        else None
        if party_id is None
        else PartyId(party_id.other_id, party_id.scheme),
        country_of_residence=pick(supplied.country_of_residence, generated.country_of_residence),
    )


def merge_agent(generated: Agent, supplied: SuppliedAgent | MISSING) -> Agent:
    if supplied is MISSING:
        return generated
    return replace(
        generated,
        bic=pick(supplied.bic, generated.bic),
        lei=pick(supplied.lei, generated.lei),
        name=pick(supplied.name, generated.name),
        address=merge_address(generated.address, supplied.address),
    )


def merge_address[A: Address | ListedAddress | None](
    generated: A, supplied: SuppliedAddress | MISSING | None
) -> Address | ListedAddress | A | None:
    if supplied is MISSING or supplied is None:
        return pick(supplied, generated)
    if isinstance(supplied.lines, list):
        return ListedAddress(tuple(supplied.lines), pick(supplied.country, generated.country if generated else None))
    base = generated if isinstance(generated, Address) else Address()
    return replace(base, **supplied.model_dump(exclude={"lines", *POSTAL_ADDRESS_27_PARTS}))


def merge_account(generated: Account, supplied: SuppliedAccount | MISSING) -> Account:
    if supplied is MISSING:
        return generated
    if supplied.iban is not MISSING:
        return Iban(supplied.iban)
    return OtherAccount(pick(supplied.other_id, ""), pick(supplied.scheme, None))


def merge_remittance(generated: Remittance, supplied: SuppliedRemittance | MISSING) -> Remittance:
    if supplied is MISSING:
        return generated
    unstructured = tuple(pick(supplied.unstructured, generated.unstructured) or ())
    structured = supplied.structured
    if structured is None:
        return Remittance(unstructured=unstructured)
    if structured is MISSING:
        return replace(generated, unstructured=unstructured)
    return Remittance(
        unstructured=unstructured,
        creditor_reference=pick(structured.creditor_reference, generated.creditor_reference),
        invoicer=pick(structured.invoicer, generated.invoicer),
        invoicee=pick(structured.invoicee, generated.invoicee),
        additional=tuple(pick(structured.additional, generated.additional) or ()),
    )
