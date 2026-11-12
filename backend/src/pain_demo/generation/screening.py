"""Generated party-name screening (spec 4.4): no generated name may match an Entity Catalogue name."""

from rapidfuzz import process, utils
from rapidfuzz.distance import JaroWinkler

from pain_demo.catalogue import Catalogue

FUZZ_THRESHOLD = 0.85


class NameScreen:
    """Exact and Jaro-Winkler matching against every catalogue name, case- and punctuation-insensitive."""

    def __init__(self, catalogue: Catalogue) -> None:
        self._names = [name.value for entity in catalogue.entities.values() for name in entity.names]

    def matches(self, name: str) -> bool:
        return (
            process.extractOne(
                name,
                self._names,
                scorer=JaroWinkler.normalized_similarity,
                processor=utils.default_process,
                score_cutoff=FUZZ_THRESHOLD,
            )
            is not None
        )
