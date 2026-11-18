"""Generated party-name screening (spec 4.4): no generated name may match an Entity Catalogue name."""

from rapidfuzz import process, utils
from rapidfuzz.distance import JaroWinkler

from pain_workbench.catalogue import Catalogue
from pain_workbench.catalogue.schema import Bank
from pain_workbench.identifiers import bic8

FUZZ_THRESHOLD = 0.85


class NameScreen:
    """Exact and Jaro-Winkler matching against every catalogue name, case- and punctuation-insensitive."""

    def __init__(self, catalogue: Catalogue) -> None:
        self._names = [name.value for entity in catalogue.entities.values() for name in entity.names]
        self._exact = {utils.default_process(name) for name in self._names}
        self._bic8s = {
            bic8(bic.value) for entity in catalogue.entities.values() if isinstance(entity, Bank) for bic in entity.bics
        }

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

    def names_entity(self, name: str) -> bool:
        """Supplied Data may not name a catalogue Entity (spec 5.3): its name, case- and punctuation-insensitive."""
        return utils.default_process(name) in self._exact

    def listed_bic(self, bic: str) -> bool:
        return bic8(bic) in self._bic8s
