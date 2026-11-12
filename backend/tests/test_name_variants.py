"""Transliteration and fuzzed Name Variants (spec 7.4, 7.5): pinned examples and the fuzz budget as a property."""

import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from rapidfuzz.distance import JaroWinkler

from pain_demo.catalogue import load_catalogue
from pain_demo.catalogue.capabilities import transliterations
from pain_demo.catalogue.schema import Entity, EntityType
from pain_demo.catalogue.transliteration import transliterate
from pain_demo.generation.fuzz import FuzzOperation, apply_operation, fuzz

CATALOGUE = load_catalogue()
SBERBANK, ALFA_BANK, EVRAZ, ABRAMOVICH = (
    CATALOGUE.entities[i] for i in ("sberbank", "alfa-bank", "evraz-plc", "roman-abramovich")
)


# --- transliteration


def test_each_scheme_romanises_a_listed_cyrillic_name_its_own_way() -> None:
    name = "ПАО Сбербанк"
    assert {
        scheme: transliterate(name, scheme)
        for scheme in ("icao", "bgn_pcgn", "iso_9", "ala_lc", "russian_passport_2013", "wikipedia")
    } == {
        "icao": "PAO Sberbank",
        "bgn_pcgn": "PAO Sberbank",
        "iso_9": "PAO Sberbank",
        "ala_lc": "PAO Sberbank",
        "russian_passport_2013": "PAO Sberbank",
        "wikipedia": "PAO Sberbank",
    }
    assert transliterate("Альфа-Банка", "bgn_pcgn") == "Al\u2019fa-Banka"
    assert transliterate("Альфа-Банка", "iso_9") == "Al\u02b9fa-Banka"
    assert transliterate("Евраз", "wikipedia") == "Yevraz"
    assert transliterate("Цюрих", "russian_passport_2013") == "Tciurikh"
    assert transliterate("Цюрих", "icao") == "Tsiurikh"


def test_an_all_capitals_word_stays_in_capitals() -> None:
    assert transliterate("Роман Аркадьевич АБРАМОВИЧ", "icao") == "Roman Arkadevich ABRAMOVICH"


def test_a_transliteration_equal_to_a_listed_latin_name_is_never_offered() -> None:
    abramovich = {(name.value, scheme): latin for name, scheme, latin in transliterations(ABRAMOVICH)}

    # Russian passport 2000 style spelling is what the UK lists: no scheme here produces it, and if one did it would
    # be left out. Wikipedia's spelling of the patronymic matches the listed one, so that scheme is left out.
    assert ("Роман Аркадьевич АБРАМОВИЧ", "wikipedia") not in abramovich
    assert abramovich[("Роман Аркадьевич АБРАМОВИЧ", "icao")] == "Roman Arkadevich ABRAMOVICH"
    listed = {name.value.casefold() for name in ABRAMOVICH.names if name.script == "latin"}
    assert not {latin.casefold() for latin in abramovich.values()} & listed


@pytest.mark.parametrize("entity", [SBERBANK, ALFA_BANK, EVRAZ, ABRAMOVICH], ids=lambda e: e.id)
def test_every_offered_transliteration_differs_from_every_listed_latin_name(entity: Entity) -> None:
    offered = transliterations(entity)
    listed = {name.value.casefold() for name in entity.names if name.script == "latin"}

    assert offered
    for name, _, latin in offered:
        assert name.script == "cyrillic"
        assert latin.casefold() not in listed


# --- fuzz operations, the spec 7.5 examples


@pytest.mark.parametrize(
    ("operation", "value", "entity_type", "expected"),
    [
        ("drop_legal_form", "Evraz PLC", "corporate", "Evraz"),
        ("drop_legal_form", "MAHAN AIR CO.", "corporate", "MAHAN AIR"),
        ("drop_legal_form", "VTB Bank (PJSC)", "bank", "VTB Bank"),
        ("abbreviate_legal_form", "Public Joint Stock Company Sberbank", "bank", "PJSC Sberbank"),
        ("abbreviate_legal_form", "JOINT STOCK COMPANY ALFA-BANK", "bank", "JSC ALFA-BANK"),
        ("expand_legal_form", "PJSC Sberbank", "bank", "Public Joint Stock Company Sberbank"),
        ("expand_legal_form", "Evraz PLC", "corporate", "Evraz Public Limited Company"),
        ("punctuation", "Alfa-Bank", "bank", "Alfa Bank"),
        ("reorder_tokens", "Roman Abramovich", "individual", "Abramovich Roman"),
        ("reorder_tokens", "Evraz PLC", "corporate", "PLC Evraz"),
        ("drop_token", "Roman Arkadyevich Abramovich", "individual", "Roman Abramovich"),
        ("drop_token", "Sberbank of Russia", "bank", "Sberbank Russia"),
        ("initial", "Roman Abramovich", "individual", "R. Abramovich"),
    ],
)
def test_a_fuzz_operation_alters_a_name_as_catalogued(
    operation: FuzzOperation, value: str, entity_type: EntityType, expected: str
) -> None:
    assert apply_operation(operation, value, entity_type, random.Random(0)) == expected


@pytest.mark.parametrize(
    ("operation", "value", "entity_type"),
    [
        ("drop_legal_form", "Sberbank", "bank"),
        ("initial", "Evraz PLC", "corporate"),
        ("drop_legal_form", "Roman Abramovich", "individual"),
        ("punctuation", "Sberbank", "bank"),
    ],
)
def test_an_operation_that_does_not_apply_gives_nothing(
    operation: FuzzOperation, value: str, entity_type: EntityType
) -> None:
    assert apply_operation(operation, value, entity_type, random.Random(0)) is None


def test_a_typo_alters_one_character_after_a_tokens_first_two() -> None:
    results = {apply_operation("typo", "Sberbank", "bank", random.Random(n)) for n in range(200)}

    assert all(result is not None and result[:2] == "Sb" for result in results)
    assert all(abs(len(str(result)) - 8) <= 1 for result in results)
    assert "Sbrebank" in results  # the spec's transposition


def test_whitespace_doubles_a_space_or_adds_a_trailing_one() -> None:
    results = {apply_operation("whitespace", "Evraz PLC", "corporate", random.Random(n)) for n in range(50)}

    assert results == {"Evraz  PLC", "Evraz PLC "}


# --- whole fuzzes, pinned per Seed so the same Seed always yields the same string (spec 7)


def test_a_seeded_fuzz_is_pinned() -> None:
    pinned = {entity.id: fuzz(random.Random("pinned"), entity) for entity in (SBERBANK, ALFA_BANK, EVRAZ, ABRAMOVICH)}

    assert {k: (f.base.value, f.operations, f.rendered) for k, f in pinned.items()} == {
        "sberbank": ("Sberbank of Russia", ("punctuation",), "Sberbank-of Russia"),
        "alfa-bank": ("ALFA-BANK", ("punctuation",), "ALFA BANK"),
        "evraz-plc": ("Evraz PLC", ("punctuation",), "Evraz-PLC"),
        "roman-abramovich": ("Roman Arkadyevich ABRAMOVICH", ("initial",), "R. Arkadyevich ABRAMOVICH"),
    }


# --- the budget, as a property


@settings(max_examples=300, deadline=None)
@given(st.sampled_from(list(CATALOGUE.entities.values())), st.integers())
def test_every_fuzz_keeps_to_the_budget(entity: Entity, seed: int) -> None:
    result = fuzz(random.Random(seed), entity)

    assert result.base in entity.names
    assert result.base.script == "latin"
    assert 1 <= len(result.operations) <= 2
    assert len(set(result.operations)) == len(result.operations)  # so at most one typo
    assert JaroWinkler.normalized_similarity(result.rendered, result.base.value) >= 0.85
    assert len(result.rendered) <= 140
    assert result.rendered.casefold() not in {name.value.casefold() for name in entity.names}
    if result.operations == ("typo",):
        base, rendered = result.base.value.split(), result.rendered.split()
        assert [token[:2] for token in base] == [token[:2] for token in rendered]
