"""Transliteration and fuzzed Name Variants (spec 7.4, 7.5): pinned examples and the fuzz budget as a property."""

import random
import re
import unicodedata

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from rapidfuzz.distance import JaroWinkler

from pain_workbench.catalogue import load_catalogue
from pain_workbench.catalogue.capabilities import MAX_NAME_LENGTH, transliterations
from pain_workbench.catalogue.schema import Entity, EntityType
from pain_workbench.catalogue.transliteration import transliterate
from pain_workbench.generation.fuzz import LEGAL_FORMS, FuzzOperation, apply_operation, fuzz, keeps_to_similarity
from pain_workbench.generation.screening import FUZZ_THRESHOLD

CATALOGUE = load_catalogue()
SBERBANK, ALFA_BANK, EVRAZ, ABRAMOVICH = (
    CATALOGUE.entities[i] for i in ("sberbank", "alfa-bank", "evraz-plc", "roman-abramovich")
)


# --- transliteration


SCHEMES = ("icao", "bgn_pcgn", "iso_9", "ala_lc", "gost_52535", "wikipedia")


def test_the_six_schemes_romanise_one_listed_name_six_ways() -> None:
    name = "Публичное Акционерное Общество Промсвязьбанк"  # Promsvyazbank's listed Cyrillic name

    assert {scheme: transliterate(name, scheme) for scheme in SCHEMES} == {
        "icao": "Publichnoe Aktsionernoe Obshchestvo Promsviazbank",
        "bgn_pcgn": "Publichnoye Aktsionernoye Obshchestvo Promsvyaz\u2019bank",
        "iso_9": "Publi\u010dnoe Akcionernoe Ob\u015destvo Promsv\u00e2z\u02b9bank",
        "ala_lc": "Publichnoe Akt\u0361sionernoe Obshchestvo Promsvi\u0361az\u02b9bank",
        "gost_52535": "Publichnoe Aktcionernoe Obshchestvo Promsviazbank",
        "wikipedia": "Publichnoye Aktsionernoye Obshchestvo Promsvyazbank",
    }


def test_a_plain_name_can_come_out_the_same_under_every_scheme() -> None:
    assert {transliterate("ПАО Сбербанк", scheme) for scheme in SCHEMES} == {"PAO Sberbank"}
    assert transliterate("Альфа-Банка", "bgn_pcgn") == "Al\u2019fa-Banka"
    assert transliterate("Альфа-Банка", "iso_9") == "Al\u02b9fa-Banka"
    assert transliterate("Евраз", "wikipedia") == "Yevraz"
    assert transliterate("Цюрих", "gost_52535") == "Tciurikh"
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


def test_a_typo_alters_only_letters_never_the_first_two_of_a_letter_run() -> None:
    value = "Alfa-Bank (PJSC)."
    results = {apply_operation("typo", value, "bank", random.Random(n)) for n in range(500)}

    for result in map(str, results):
        assert re.sub(r"[^\W\d_]", "", result) == "- ().", result
        assert [run[:2] for run in re.findall(r"[^\W\d_]+", result)] == ["Al", "Ba", "PJ"], result
        assert all(run.isupper() for run in re.findall(r"[^\W\d_]+", result)[2:]), result


def test_punctuation_changes_only_the_punctuation_it_targets() -> None:
    results = {apply_operation("punctuation", "Alfa-Bank,  Moscow.", "bank", random.Random(n)) for n in range(200)}

    assert results == {"Alfa Bank,  Moscow.", "Alfa-Bank,  Moscow", "Alfa-Bank,- Moscow.", "Alfa-Bank, -Moscow."}


def test_whitespace_doubles_a_space_or_adds_a_trailing_one() -> None:
    results = {apply_operation("whitespace", "Evraz PLC", "corporate", random.Random(n)) for n in range(50)}

    assert results == {"Evraz  PLC", "Evraz PLC "}


def test_the_similarity_budget_ignores_token_order_but_not_letters() -> None:
    assert keeps_to_similarity("Abramovich Roman", "Roman Abramovich")
    assert JaroWinkler.normalized_similarity("Abramovich Roman", "Roman Abramovich") < FUZZ_THRESHOLD  # unsorted
    assert not keeps_to_similarity("Roman Vekselberg", "Roman Abramovich")


def test_reorder_tokens_appears_in_drawn_fuzzes() -> None:
    drawn = [fuzz(random.Random(n), ABRAMOVICH) for n in range(200)]

    assert any("reorder_tokens" in f.operations for f in drawn)


# --- whole fuzzes, pinned per Seed so the same Seed always yields the same string (spec 7)


def test_a_seeded_fuzz_is_pinned() -> None:
    pinned = {entity.id: fuzz(random.Random("pinned"), entity) for entity in (SBERBANK, ALFA_BANK, EVRAZ, ABRAMOVICH)}

    assert {k: (f.base.value, f.operations, f.rendered) for k, f in pinned.items()} == {
        "sberbank": ("Sberbank of Russia", ("punctuation",), "Sberbank-of Russia"),
        "alfa-bank": ("ALFA-BANK", ("punctuation",), "ALFA BANK"),
        "evraz-plc": ("Evraz PLC", ("punctuation",), "Evraz-PLC"),
        "roman-abramovich": ("Roman ABRAMOVICH", ("reorder_tokens",), "ABRAMOVICH Roman"),
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
    tokens_sorted = [" ".join(sorted(v.split())) for v in (result.rendered, result.base.value)]
    assert JaroWinkler.normalized_similarity(*tokens_sorted) >= FUZZ_THRESHOLD
    assert len(result.rendered) <= MAX_NAME_LENGTH
    assert result.rendered.casefold() not in {name.value.casefold() for name in entity.names}
    if "typo" in result.operations:  # every word starts as a word of the base (punctuation dropped or not) or a form
        base = result.base.value
        words = [base, re.sub(r"[^\w\s-]", "", base), *LEGAL_FORMS, *LEGAL_FORMS.values()]
        allowed = {run[:2] for run in _letter_runs(" ".join(words))}
        for run in _letter_runs(result.rendered):
            assert any(prefix.startswith(run[:2]) for prefix in allowed), (result, run)


def _letter_runs(value: str) -> list[str]:
    bare = "".join(c for c in unicodedata.normalize("NFD", value) if not unicodedata.combining(c))
    return re.findall(r"[^\W\d_]+", bare.casefold())
