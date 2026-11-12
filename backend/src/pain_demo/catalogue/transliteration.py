"""Transliteration Name Variant (spec 7.4): a listed Cyrillic name romanised under a named scheme, on no list."""

import re
from typing import Literal

import iuliia

type TransliterationScheme = Literal["icao", "bgn_pcgn", "iso_9", "ala_lc", "russian_passport_2013", "wikipedia"]

SCHEMES: dict[TransliterationScheme, iuliia.Schema] = {
    "icao": iuliia.ICAO_DOC_9303,
    "bgn_pcgn": iuliia.BGN_PCGN,
    "iso_9": iuliia.GOST_779,  # GOST 7.79-2000 system A is ISO 9:1995
    # iuliia has no separate 2013 passport scheme (2013 passports use ICAO Doc 9303, already above), so the slot
    # takes GOST R 52535.1-2006, the passport scheme in force until 2013, whose output differs from ICAO's.
    "russian_passport_2013": iuliia.GOST_52535,
    "ala_lc": iuliia.ALA_LC,
    "wikipedia": iuliia.WIKIPEDIA,
}
"""The curated six, in draw order: the order feeds the RNG, so changing it changes every Seed's transliterations."""


def transliterate(value: str, scheme: TransliterationScheme) -> str:
    """Word by word, an all-capitals word stays in capitals (iuliia alone writes `ABRAMOVICh`)."""

    def word(match: re.Match[str]) -> str:
        latin = SCHEMES[scheme].translate(match[0])
        return latin.upper() if match[0].isupper() else latin

    return re.sub(r"\S+", word, value)
