# Seeded fake payment data libraries

Research for [#4](https://github.com/Tryline-Studios/pain-demo/issues/4), part of the wayfinder map [#1](https://github.com/Tryline-Studios/pain-demo/issues/1).

**Question.** Which Python libraries can produce realistic, country-appropriate Generated Data (party names, structured addresses, checksum-valid IBANs, plausible BICs, amounts, currencies) that is reproducible from a Seed and runs on Python 3.13? How do the candidates compare on IBAN/BIC validity, per-country locales, determinism, licence and maintenance?

Researched 2026-09-16. Versions tested: Faker 40.39.0, schwifty 2026.7.3 and mimesis 21.0.0, all on CPython 3.13.6 via `uv`.

## Answer

Use **Faker for people and places** and **schwifty for bank details**. Pin both to exact versions, and build amounts and currencies ourselves from the same seeded `random.Random`.

- **Faker** covers names, company names and structured address parts (street, building number, postcode, town) for every EU/UK/US locale we care about. Each request needs its own generator, seeded with `seed_instance()`. Faker's `iban()` passes the IBAN mod-97 check, but in 7 of 37 locales it fails the national BBAN checksum, in 11 of 37 it produces nothing schwifty accepts as an IBAN, and it cannot produce real banks. Don't use it for bank details.
- **schwifty** `IBAN.random(country_code, random=rng)` picks a real bank from its registry. Its IBANs pass the national BBAN checksums, and `iban.bic` gives that bank's real BIC. Two caveats:
  - **The registry contains sanctioned banks**, including Bank Melli Iran, Bank Saderat Iran, Bank Sepah, Bank Mellat, VTB Bank Georgia and Sberbank. An unfiltered draw can put a real Sanctioned Entity into a clean Sample File.
  - For some countries the account part can contain random letters.

  Fix both by drawing from an allowlist of registry banks and passing a numeric `account_code` we generate ourselves.
- **Reproducibility only holds for exact library versions.** Faker says so itself, and in our tests schwifty's seeded output changed between two patch releases. Pin exact versions and treat any upgrade as a change that breaks existing Seeds.
- **mimesis** is not a fit: it has no IBAN or BIC generator, and its current release fails to import on a clean install.

## Comparison

| | Faker 40.39.0 | schwifty 2026.7.3 | mimesis 21.0.0 |
|---|---|---|---|
| Purpose | General fake data | IBAN/BIC parsing, validation and generation | General fake data |
| Checksum-valid IBANs | mod-97 always valid for supported countries; national BBAN checksum fails 90-99% for FR, IT, PT, SK, CZ, PL, FI (E1) | mod-97 and national BBAN checksums valid in 18/18 countries tested (E2) | No IBAN generator (S12) |
| IBAN countries | 37 bank locales; 11 produce invalid IBANs, and en_US (no bank locale) gets GB ones (E1) | Every country in its IBAN registry; bank registry covers 45 countries (E2) | n/a |
| BIC | Random format, never a real bank (E3); 8.6% fail the pain.001.001.03 `BICIdentifier` pattern (E6) | Real BIC of the drawn bank via `iban.bic`; missing for 0-31% of draws in some countries (E2) | n/a |
| Names / companies | Locale-appropriate, many locales (E4) | n/a | Locale-appropriate, 48 locales (E4) |
| Structured address | `street_name`, `building_number`, `postcode`, `city`, `current_country_code` for en_GB, en_IE, en_US, de_DE, fr_FR, it_IT, es_ES, nl_NL, nl_BE, pl_PL, de_AT, pt_PT (E4) | n/a | `street_name`, `street_number`, `postal_code`, `city`; no en-IE locale (E4) |
| Currency / amount | `currency_code()` draws from all world currencies, not the locale's (E4, S4) | n/a | `currency_iso_code()` |
| Seeding | `seed_instance()` gives each generator its own `random.Random` (S3) | Accepts a `random: Random` argument (S6) | `seed=` per provider (S13) |
| Same seed, same process | Identical (E5) | Identical (E5) | Identical (E4) |
| Same seed across versions | Not guaranteed (S2); changed in our tests (E7) | Changed between patch releases (E7) | Not tested |
| Python 3.13 | Classifier and tested (S1, E*) | Classifier and tested (S5, E*) | Classifier present, but the wheel fails to import (E8) |
| Licence | MIT (S1) | MIT (S5) | MIT (S11) |
| Maintenance | ~19.4k stars; releases roughly every 1-2 weeks; last push 2026-09-15 (S1, S10) | ~260 stars; 6 releases in 2026; last push 2026-09-15 (S5, S10) | ~4.8k stars; releases 20.0.0 and 21.0.0 in July 2026 (S11, S10) |

## Findings

### 1. IBANs

**Faker computes the mod-97 check digits but not national BBAN checksums.** `bban()` fills a locale `bban_format` with random letters and digits, then `iban()` calculates the ISO 7064 check digits over it (S4). The docstring only promises that values are "valid in form" (S4).

In E1, 2,000 IBANs per locale were validated with schwifty's `validate(validate_bban=True)`:

- **Fine for 19 locales:** az_AZ, da_DK, de_AT, de_CH, de_DE, el_GR, en_GB, en_IE, es_ES, fr_CH, it_CH, nl_BE, nl_NL, pt_BR, ro_RO, ru_RU, tr_TR and uk_UA had 0% failures, and no_NO had about 1%.
  - For de_DE and en_GB, 0% of the IBANs resolved to a bank in schwifty's registry (E3). The bank codes are invented, so Germany's bank-specific account check digit is never tested.
- **National checksum fails for 7 locales:** fr_FR 99%, it_IT 97%, pt_PT 99%, sk_SK 99%, cs_CZ 99%, pl_PL 90% and fi_FI 90%.
- **Not a valid IBAN for 11 locales:**
  - bn_BD, en_PH, fil_PH, tl_PH, es_AR and th_TH use countries with no IBAN, so schwifty reports `InvalidCountryCode`.
  - fa_IR and mk_MK have the wrong length.
  - en_IN, es_MX and zh_CN have no bank provider of their own. Faker falls back to the provider's `default_locale = "en_GB"` (S4, S3), so they produce GB-prefixed IBANs, which fail the length check.
- **en_US silently returns GB IBANs**, e.g. `GB94EDLY49018232359413`. There is no en_US bank provider, so the same fallback applies (E1, S3). This is expected, because the US does not use IBANs (schwifty rejects `US` too, E3). Faker's `aba()` does generate a checksum-valid ABA routing number (S4).

**schwifty generates national-checksum-valid IBANs from real banks.** `BBAN.random` works like this (S6):

1. Pick a bank from the country's registry, unless `use_registry=False`.
2. Fill the BBAN from the country's regex with `rstr` driven by the supplied `Random`.
3. Solve the national checksum. Since 2026.07.3 it builds a valid checksum directly instead of retrying random BBANs until one validates (S7).

The docs confirm that "the bank code will be taken from there, so that the IBAN corresponds to a valid bank" (S8).

In E2, 1,000 IBANs per country for DE, GB, FR, IT, ES, NL, BE, AT, IE, PT, PL, CZ, SK, FI, CH, SE, DK and LU all passed `validate(validate_bban=True)`. The bank registry covers 45 countries: AD, AE, AT, BA, BE, BG, CH, CR, CY, CZ, DE, DK, EE, ES, FI, FR, GB, GE, GR, HR, HU, IE, IL, IS, IT, KZ, LI, LT, LU, LV, MC, MD, ME, NL, NO, PL, PT, RO, RS, SA, SE, SI, SK, TR and UA (E2).

**Realism caveat.** Where the IBAN registry allows alphanumeric account codes, schwifty fills them with random letters. For example FR allows `[A-Za-z0-9]{11}`, and IT, CH and LU are similar (E3). That gives values like `FR941426564710IB3ECD44WB693` and `LU89423H18YBC3V2VNYD` (E2), which are valid but unlike real accounts. `IBAN.random` accepts components as keyword arguments (S6), and passing a numeric `account_code` still gave 200/200 valid IBANs for FR, IT, CH and LU (E3), e.g. `FR76 1980 6391 5029 1417 7763 166`.

`IBAN.generate(country, bank_code, account_code)` builds an IBAN from components without using randomness (S6). It fills in the national checksum for GB, FR, IT, ES, NL and BE (0% failures in E9). **It does not solve Germany's check digit, which is embedded in the account code:** 88% of random DE account codes failed (E9). For DE, use `IBAN.random(..., bank_code=...)`.

### 2. BICs

- **Faker's `swift()`** builds the bank code from four random letters, then adds the locale's country code and a random 2-character location code. Branch codes are random too. `use_dataset=True` only takes codes from a locale's data if the locale provides them (S4). **None of the 3,000 codes produced with `use_dataset=True` (500 each for de_DE, en_GB, fr_FR, nl_NL, it_IT and es_ES) exist in schwifty's BIC registry (E3).**
  - The location code is drawn from `A-Z0-9`, but the pain.001.001.03 XSD `BICIdentifier` pattern `[A-Z]{6,6}[A-Z2-9][A-NP-Z0-9]([A-Z0-9]{3,3}){0,1}` forbids `0` or `1` as the 7th character and `O` as the 8th (S9).
  - In E6, **8.64% of Faker's `swift()` values failed that pattern**, so they would make a Sample File fail schema validation.
  - schwifty's `BIC(...).validate(enforce_swift_compliance=True)` accepted all of them, so don't rely on it to catch this (E6).
- **schwifty has no `BIC.random`.** Its public generation API is `IBAN.random` / `BBAN.random`; `BIC` has only constructors and lookups (S6). The practical route is `iban.bic`, the registry BIC of the bank the IBAN was drawn from (S6).
  - Every BIC returned in E2 validated.
  - Some registry banks have no BIC. Draws without one: ES 31%, CZ 28%, PT 10%, SK 8%, DK 7%, PL 4%, BE 3%, CH 2%, and 0% for DE, GB, FR, IT, NL, AT, IE, FI, SE and LU (E2).
  - `BIC.exists` means "available in Schwifty's registry" (S6).

**These are real banks, which matters for this app.** A regex search of the registry for sanctioned-bank names found the following (E10):

- DE: Bank Melli Iran Hamburg (`MELIDEHHXXX`), Bank Saderat Iran Hamburg and Frankfurt (`SIHRDEH1HAM`, `SIHRDEH1FFM`), Bank Sepah-Iran Frankfurt (`SEPBDEFFXXX`)
- TR: Bank Mellat (`BKMTTRIS`)
- GE: VTB Bank Georgia (`UGEBGE22`)
- BA: Sberbank a (`SABRBA2BXXX`)
- CZ: Sberbank CZ in liquidation

Germany has 4,803 registry entries, 4 of which are the Iranian banks above. A clean 100-transaction all-DE Sample File therefore has about an **8% chance** of naming one of them (E10). The search was a quick name scan, not a check against OFAC or OFSI lists, so there may be more.

### 3. Names and structured addresses

**Faker** has separate methods for every structured-address field in pain.001.001.03 `PostalAddress6`: `StrtNm` Max70, `BldgNb` Max16, `PstCd` Max16, `TwnNm` Max35, `Ctry` (S9). Sample output from E4, seed 1:

| Locale | Name | Street | Bldg | Postcode | Town |
|---|---|---|---|---|---|
| en_GB | Ruth Baker | Jones Light | 1 | BB66 7LJ | West Roberttown |
| en_IE | Seamus Combre | O'Rafferty Street | 17 | A66 7YP8 | Kirby Ville |
| en_US | Ryan Gallagher | Pearson Turnpike | 17066 | 80119 | Lake Seanbury |
| de_DE | Karsten Wieloch-Bolnbach | Mudeweg | 4-2 | 06690 | Groß-Gerau |
| fr_FR | Roland Salmon | avenue Charlotte Gilles | 23 | 62129 | LesageVille |
| it_IT | Azeglio Gualtieri | Canale Parisi | 171 | 67030 | Glorie |
| es_ES | Lucas Barroso Jara | Ronda de Ema Abril | 44 | 39741 | Guadalajara |
| nl_NL | Matthijs Dekker | Wesleyweg | 3 | 7706MW | 's-Heer Hendrikskinderen |
| pl_PL | Nicole Hirsch | Pałacowa | 763 | 13-500 | Bydgoszcz |

Notes:

- **Postcodes have the right format but aren't real, and don't match the town.**
- **Town realism varies by locale.** de_DE, es_ES, pl_PL and pt_PT use real town names. en_GB, en_US and fr_FR use invented ones such as "West Roberttown" and "LesageVille".
- **Neither issue matters for schema validity.**
- **Town names can be too long.** Over 5,000 draws per locale, only it_IT produced towns over the `TwnNm` limit of 35 characters (2 draws, max 37). Every other field stayed within its limit (E6). The generator should still check lengths.
- **Multi-locale generators aren't a safe way to get a specific country.** `Faker(["de_DE", "fr_FR"])` picks a locale per call, so one party can get a German name and a French address (S3). Keep one generator per country.

**mimesis** has equivalent fields and 48 locales, but none for en-IE (E4). Tested with seed 1 on four locales, every locale gave the same street number (`1166`), and en, de and fr gave the same postcode (`87244`). Postcodes are drawn from the shared random stream without a per-locale pattern, so they are not realistic.

### 4. Amounts and currencies

Neither library adds anything useful here.

- Faker's `currency_code()` is `self.currency()[0]` (S4), a uniform pick from all world currencies. With seed 1 it gave ARS for en_GB and HTG for de_DE (E4).
- pain.001.001.03 amounts are `xs:decimal` with `fractionDigits` 5 and `totalDigits` 18 (S9).

Build amounts ourselves:

1. Map each country to its currency (e.g. EUR, GBP, USD).
2. Draw from the per-Sample-File `random.Random`.
3. Quantize a `Decimal` to that currency's minor units.

This is simpler and does not depend on either library's version.

### 5. Determinism under a Seed

**Within one process and version:**

- **Faker:** `Faker.seed()` seeds one module-level `random.Random` shared by every generator (S3; E5 confirmed `a.random is b.random`), so concurrent requests would interfere. `seed_instance()` swaps in a private `random.Random` for that generator (S3).
  - In E5, 64 generation tasks across 16 threads, alternating fr_FR seed 123 and de_DE seed 999, each reproduced the single-threaded output exactly.
  - Calls to the global `random` module did not change a `seed_instance`d generator's output (E5).
- **schwifty:** the same `Random(seed)` gave the same IBAN (E5).
- **Both depend on call order.** Every draw advances the shared stream, so adding or reordering a field shifts every later value. Deriving a sub-seed per transaction limits the damage.

**Across library versions, output is not stable.**

- Faker's README says: "results are not guaranteed to be consistent across patch versions. If you hardcode results in your test, make sure you pinned the version of Faker down to the patch number" (S2).
- E7 generated the same seeded data under five version pairs:

| Faker / schwifty | Faker en_GB | Faker de_DE | Faker fr_FR, en_US | schwifty IBANs identical to 2026.7.3 |
|---|---|---|---|---|
| 40.38.0 / 2026.7.2 | same | same | same | **12/60** |
| 40.30.0 / 2026.7.0 | same | same | same | 33/60 |
| 37.12.0 / 2026.3.0 | `street_name` changed in 30/30 rows | same | same | 50/60 |
| 33.3.1 / 2025.1.0 | `street_name` changed | ~all fields changed | same | 36/60 |

- **Why schwifty changes:**
  - 2026.07.3 changed `BBAN.random` to construct checksums directly, which changes how many random draws it uses (S7). That explains the 12/60 against 2026.7.2 one patch release earlier.
  - Registry data is also updated frequently. For example, the unreleased changelog adds banks to MT, GB, FR, ES, CY, BG, PT, TR and PK (S7), and new banks change which bank a seeded `random.choice` picks.
  - The public API moves too: `registry.get_banks_by_country` was absent in 2025.1.0 (E9) and helpers were removed in 2026.07.2 (S7).
- **Pin both packages exactly** (`==`, committed `uv.lock`). Add a golden Sample File test (fixed request plus Seed, compared byte for byte) so an upgrade that breaks existing Seeds fails CI rather than silently changing old Seeds.

### 6. Python 3.13, licence, maintenance

- **Faker 40.39.0:** MIT; `requires_python >=3.10`; classifiers include 3.13 and 3.14. Its only runtime dependency is `tzdata`, and only on Windows (S1). There were six releases between 2026-07-22 and 2026-09-14 (S1). The repo is active, last pushed 2026-09-15, with ~19.4k stars (S10).
- **schwifty 2026.7.3:** MIT; `>=3.10`; classifiers include 3.13 and 3.14. It depends on `pycountry` and `rstr` (S5). There have been 6 releases in 2026 (S5). The repo is active, last pushed 2026-09-15, with ~260 stars and effectively a single maintainer (S10). CalVer versioning `YY.0M.Micro` means version numbers say nothing about breaking changes (S7).
- **mimesis 21.0.0:** MIT, `>=3.10`, with 3.13 and 3.14 classifiers and `dependencies = []` (S11). However, `mimesis/providers/generic.py` does `from typing_extensions import Self` (S12). On a clean `uv add mimesis` under 3.13, `import mimesis` raises `ModuleNotFoundError: No module named 'typing_extensions'` (E8). The file on `master` still has that import, and no issue mentioning `typing_extensions` exists in the repo (S12, S10). It works once `typing_extensions` is installed separately.
- **Performance is not a concern.** Importing Faker and schwifty took 0.08 s. The first `IBAN.random` call, which loads the registry, took 0.05 s. A warm `Faker("de_DE")` took 0.4 ms, and 100 DE IBANs took 7.7 ms (E11).

## Recommendation

1. **Dependencies:** add `faker` and `schwifty` at exact versions. Don't add mimesis.
2. **Seed:** each Sample File gets one `random.Random` derived from the Seed.
   - For each transaction, derive a sub-seed from it.
   - Create one Faker generator per country and call `seed_instance(sub_seed)` on it. Never use `Faker.seed`.
   - Pass a `random.Random(sub_seed)` to schwifty.
3. **Parties:** get the name or company and `StrtNm`, `BldgNb`, `PstCd` and `TwnNm` from Faker, using our own map from country to locale. Set `Ctry` from our country code, not from Faker, and check the XSD length limits.
4. **Accounts and agents (IBAN countries):**
   - Call `IBAN.random(cc, random=rng, bank_code=<allowlisted>, account_code=<numeric, generated by us>)`. The account code override matters for countries whose IBAN format allows letters.
   - Use `iban.bic` as the agent BIC, and skip allowlist entries without a BIC.
   - Build the allowlist from the pinned schwifty registry and check it against the Entity Catalogue and sanctions lists, so Generated Data never names a real Sanctioned Entity by accident.
5. **US parties:** the US has no IBAN.
   - Use a non-IBAN account (`Othr/Id`) with an ABA routing number. Faker's `aba()` can supply one.
   - Take the agent BIC from a small curated list of real US banks; schwifty has no US bank registry.
6. **Amounts and currencies:** generate them ourselves as described in Finding 4.
7. **Reproducibility:** a Seed is reproducible only for a given app build. Record the app version, or the locked Faker and schwifty versions, with the Sample File or Answer Key, and add a golden-file test.

## Open questions and risks (not resolved here)

- **Sanctioned banks in clean files.** The schwifty registry names real sanctioned banks (Finding 2). Is the allowlist part of the Entity Catalogue work, or a separate list? Which banks are acceptable as "clean"?
- **Fake names matching real sanctions entries.** Faker party names could loosely match real sanctions entries and trigger unplanned alerts on a clean file. This was not tested.
- **Seeds across versions.** Is a Seed expected to reproduce across app upgrades? If so, the Seed contract must include a generator version, or we must vendor the data.

## Sources

- **S1** Faker on PyPI, JSON metadata (version, licence, `requires_python`, classifiers, releases): https://pypi.org/pypi/faker/json, https://pypi.org/project/Faker/40.39.0/
- **S2** Faker README, "Seeding the Generator": https://github.com/joke2k/faker/blob/v40.39.0/README.rst#seeding-the-generator
- **S3** Faker source:
  - `generator.py`: module-level shared `random = random_module.Random()`, `seed_instance` creates a per-instance `Random`, `seed` seeds the shared one: https://github.com/joke2k/faker/blob/v40.39.0/faker/generator.py
  - `proxy.py`: multi-locale proxy: https://github.com/joke2k/faker/blob/v40.39.0/faker/proxy.py
  - `factory.py`: `_find_provider_class` falls back to the provider's `default_locale`: https://github.com/joke2k/faker/blob/v40.39.0/faker/factory.py
- **S4** Faker source:
  - Bank provider (`bban`, `iban`, `swift`, `aba`, `default_locale = "en_GB"`, "valid in form" disclaimer): https://github.com/joke2k/faker/blob/v40.39.0/faker/providers/bank/__init__.py
  - Currency provider: https://github.com/joke2k/faker/blob/v40.39.0/faker/providers/currency/__init__.py
- **S5** schwifty on PyPI, JSON metadata: https://pypi.org/pypi/schwifty/json, https://pypi.org/project/schwifty/2026.7.3/
- **S6** schwifty source:
  - `bban.py` (`BBAN.random`, registry pick, `rstr`, checksum solving): https://github.com/mdomke/schwifty/blob/2026.07.3/schwifty/bban.py
  - `iban.py` (`IBAN.random`, `IBAN.generate`, `validate(validate_bban=...)`, `bic`, `bank`): https://github.com/mdomke/schwifty/blob/2026.07.3/schwifty/iban.py
  - `bic.py` (no random constructor; `exists` = "available in Schwifty's registry"): https://github.com/mdomke/schwifty/blob/2026.07.3/schwifty/bic.py
- **S7** schwifty changelog (CalVer scheme; 2026.07.3 `BBAN.random` change; 2026.07.2 registry API changes; unreleased registry additions): https://github.com/mdomke/schwifty/blob/main/CHANGELOG.rst
- **S8** schwifty docs, "Random IBANs": https://github.com/mdomke/schwifty/blob/main/docs/source/examples.rst, https://schwifty.readthedocs.io/en/latest/examples.html
- **S9** pain.001.001.03 XSD bundled with the `pain001` package (`templates/pain.001.001.03/pain.001.001.03.xsd`): `PostalAddress6`, `Max16Text`/`Max35Text`/`Max70Text`/`Max140Text`, `BICIdentifier`, `IBAN2007Identifier`, `ActiveOrHistoricCurrencyAndAmount_SimpleType`
- **S10** GitHub repository metadata via `gh api repos/<owner>/<repo>` and `gh search issues`, 2026-09-16: https://github.com/joke2k/faker, https://github.com/mdomke/schwifty, https://github.com/lk-geimfari/mimesis
- **S11** mimesis on PyPI, JSON metadata and `pyproject.toml`: https://pypi.org/pypi/mimesis/json, https://github.com/lk-geimfari/mimesis/blob/master/pyproject.toml
- **S12** mimesis source: `finance.py` (no IBAN/BIC methods), `generic.py` (`from typing_extensions import Self`): https://github.com/lk-geimfari/mimesis/blob/v21.0.0/mimesis/providers/finance.py, https://github.com/lk-geimfari/mimesis/blob/master/mimesis/providers/generic.py
- **S13** mimesis source, `BaseProvider(seed=...)`: https://github.com/lk-geimfari/mimesis/blob/v21.0.0/mimesis/providers/base.py

## Experiments

All experiments ran in a scratch `uv` project outside the repo on CPython 3.13.6, with Faker 40.39.0 and schwifty 2026.7.3 unless stated otherwise.

- **E1** For each of Faker's 37 bank locales: `Faker(loc).seed_instance(1)`, 2,000 × `iban()`, each parsed with `schwifty.IBAN(s)` and then `.validate(validate_bban=True)`.
- **E2** For 18 countries: 1,000 × `IBAN.random(cc, random=Random(42))`, then `validate(validate_bban=True)`, then `iban.bic` checked with `BIC(str(bic))`. Also `registry.get_countries()`.
- **E3**
  - 500 × `swift(use_dataset=True)` for each of 6 locales, checked with `BIC(...).exists`.
  - `IBAN(faker.iban()).bank is not None` for de_DE and en_GB.
  - `IBAN.random("US")` raised `InvalidCountryCode`.
  - BBAN specs read from `_get_bban_spec`.
  - `IBAN.random(cc, random=Random(1), account_code=<digits>)` for FR, IT, CH and LU (200 each).
- **E4** Faker structured address and name methods for 12 locales, seed 1. mimesis `Address`/`Person` with `seed=1` for en-gb, de, fr and en.
- **E5**
  - Faker regenerated with the same seed in the same process.
  - 64 tasks on a 16-thread `ThreadPoolExecutor`, each creating its own `seed_instance`d generator, compared with single-threaded output.
  - `Faker.seed` shared-`Random` identity check.
  - Global `random.seed` interference check.
  - schwifty with the same `Random(7)` three times.
- **E6**
  - 5,000 × `swift()` per locale matched against the XSD `BICIdentifier` regex and checked with `BIC.validate(enforce_swift_compliance=True)`.
  - Maximum field lengths over 5,000 draws per locale against the `PostalAddress6` limits.
- **E7** The same script under `uv run --no-project --with faker==X --with schwifty==Y` for 40.39.0/2026.7.3, 40.38.0/2026.7.2, 40.30.0/2026.7.0, 37.12.0/2026.3.0 and 33.3.1/2025.1.0: 30 rows × 4 locales of Faker fields with `seed_instance(123)`, plus 60 `IBAN.random` values from `Random(123)`. Outputs compared field by field.
- **E8** `uv add faker schwifty mimesis` in a fresh 3.13 project, then `import mimesis`.
- **E9**
  - 300 × `IBAN.generate(cc, bank_code, account_code=<random digits>)`, then `validate(validate_bban=True)`, for DE, GB, FR, IT, ES, NL and BE.
  - The same script under schwifty 2025.1.0 failed on `registry.get_banks_by_country`.
- **E10** Regex scan of bank names in every registry country (`registry.get_banks_by_country`) for sanctioned-bank names. DE entry count, and the probability of drawing at least one of the 4 sanctioned DE entries in 100 draws: 1 − (1 − 4/4803)^100 ≈ 0.08.
- **E11** Wall-clock timings with `time.perf_counter()`.
