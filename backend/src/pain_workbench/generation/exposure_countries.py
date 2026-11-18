"""The six Exposure countries (spec 8.2, 8.3): their currencies and curated cities, as code constants."""

from dataclasses import dataclass
from typing import Literal

type ExposureCountry = Literal["RU", "BY", "IR", "KP", "SY", "VE"]


@dataclass(frozen=True)
class ExposureProfile:
    currency: str
    """An exposed transaction is paid in it whatever `currencies` says (spec open point 4)."""
    cities: tuple[str, ...]


EXPOSURE_COUNTRIES: dict[ExposureCountry, ExposureProfile] = {
    "RU": ExposureProfile("RUB", ("Moscow", "St Petersburg", "Novosibirsk", "Yekaterinburg", "Kazan")),
    "BY": ExposureProfile("BYN", ("Minsk", "Gomel", "Brest", "Grodno", "Vitebsk")),
    "IR": ExposureProfile("IRR", ("Tehran", "Mashhad", "Isfahan", "Tabriz", "Shiraz")),
    "KP": ExposureProfile("KPW", ("Pyongyang", "Hamhung", "Chongjin", "Nampo", "Wonsan")),
    "SY": ExposureProfile("SYP", ("Damascus", "Aleppo", "Homs", "Latakia", "Hama")),
    "VE": ExposureProfile("VES", ("Caracas", "Maracaibo", "Valencia", "Barquisimeto", "Maracay")),
}
"""In `ExposureCountry` order, which `GET /options` publishes and the default request lists."""
