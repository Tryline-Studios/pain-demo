"""`just build-clean-banks`: rewrite the IBAN-country section of the Clean Bank List from schwifty (spec 4.2).

For each IBAN country it takes every registry bank with a BIC, drops anything matching the Entity Catalogue by BIC
or by name, and keeps about 25 spread evenly through the alphabet so the output is stable across runs. Entries are
sorted by normalised name, so the mixed case of registry names does not scatter the order. The United States section
of the file is hand-maintained (there is no US registry) and is copied through untouched. A human reviews the diff
before committing, and any change regenerates the goldens and bumps the minor version (spec 15.4).

Dropping by name is stricter here than the startup assertion: a registry bank goes when the words of any catalogue
Bank's Latin name appear in order inside its own name (so "Bank Sepah-Iran" goes for "Bank Sepah"), or when its
normalised name equals any catalogue name.
"""

import importlib.metadata
from pathlib import Path

from schwifty import registry

from pain_workbench.catalogue import Catalogue, load_catalogue
from pain_workbench.generation.clean_banks import (
    DEFAULT_PATH,
    IBAN_COUNTRIES,
    CatalogueIndex,
    CleanBank,
    IbanCountry,
    normalise_name,
)
from pain_workbench.identifiers import bic8, bic_country

BANKS_PER_COUNTRY = 25
US_SECTION_MARKER = "# --- United States"

HEADER = """\
# The Clean Bank List (spec section 4): the real, non-sanctioned banks Generated Data draws agents and accounts from.
# Everything above the United States marker is written by `just build-clean-banks` from schwifty's bank registry
# (schwifty {schwifty_version}) minus every bank matching the Entity Catalogue by BIC or name; do not edit it by hand.
# The United States section is hand-maintained: schwifty has no US registry.
"""


def build(catalogue: Catalogue, path: Path = DEFAULT_PATH) -> str:
    """Return the new file contents: a fresh IBAN-country section followed by the file's current US section."""
    us_section = _us_section(path)
    index = CatalogueIndex(catalogue)
    banks = [bank for country in sorted(IBAN_COUNTRIES) for bank in registry_banks(country, index)]
    header = HEADER.format(schwifty_version=importlib.metadata.version("schwifty"))
    return "\n".join([header, *(_render(bank) for bank in banks), us_section])


def registry_banks(country: IbanCountry, index: CatalogueIndex) -> list[CleanBank]:
    """About 25 registry banks for one country that match nothing in the catalogue, sorted by normalised name."""
    candidates: dict[str, CleanBank] = {}
    seen_codes: set[str] = set()
    seen_bic8: set[str] = set()
    for record in sorted(registry.get_banks_by_country(country), key=lambda r: (not r.primary, r.bank_code)):
        name = " ".join(record.name.split())
        normalised = normalise_name(name)
        if not record.bic or bic_country(record.bic) != country or not normalised:
            continue  # no BIC, a foreign BIC (registries list branches of foreign banks), or a blank name
        if record.bank_code in seen_codes or bic8(record.bic) in seen_bic8 or normalised in candidates:
            continue  # one entry per bank code, per institution and per name
        if bic8(record.bic) in index.bic8s or normalised in index.names:
            continue
        if any(_contains(normalised.split(), words) for words in index.bank_name_words):
            continue
        seen_codes.add(record.bank_code)
        seen_bic8.add(bic8(record.bic))
        candidates[normalised] = CleanBank(country=country, bank_code=record.bank_code, bic=record.bic, name=name)

    by_name = [candidates[key] for key in sorted(candidates)]
    return spread(by_name, BANKS_PER_COUNTRY)


def spread[T](items: list[T], count: int) -> list[T]:
    """`count` items spread evenly through `items`, keeping their order; all of them when there are fewer."""
    if len(items) <= count:
        return items
    return [items[(index * len(items)) // count] for index in range(count)]


def _contains(haystack: list[str], needle: list[str]) -> bool:
    width = len(needle)
    return any(haystack[start : start + width] == needle for start in range(len(haystack) - width + 1))


def _render(bank: CleanBank) -> str:
    return (
        "[[banks]]\n"
        f'country = "{bank.country}"\n'
        f'bank_code = "{bank.bank_code}"\n'
        f'bic = "{bank.bic}"\n'
        f"name = {_toml_string(bank.name)}\n"
    )


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _us_section(path: Path) -> str:
    if not path.is_file():
        return f"{US_SECTION_MARKER} (hand-maintained; each entry also carries its ABA routing number) ---\n"
    text = path.read_text(encoding="utf-8")
    marker = text.find(US_SECTION_MARKER)
    if marker < 0:
        msg = f"{path.name} has no {US_SECTION_MARKER!r} marker; the US section could not be kept"
        raise ValueError(msg)
    return text[marker:]


def main() -> None:
    DEFAULT_PATH.write_text(build(load_catalogue()), encoding="utf-8")
    print(f"wrote {DEFAULT_PATH}")


if __name__ == "__main__":
    main()
