"""Fuzzed Name Variant (spec 7.5): a listed Latin name altered by at most two catalogued operations."""

import random
import re
import string
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from rapidfuzz.distance import JaroWinkler

from pain_demo.catalogue.capabilities import LEGAL_ENTITIES, MAX_NAME_LENGTH, candidate_names
from pain_demo.catalogue.schema import Entity, EntityType, Name
from pain_demo.generation.screening import FUZZ_THRESHOLD

type FuzzOperation = Literal[
    "typo",
    "drop_legal_form",
    "abbreviate_legal_form",
    "expand_legal_form",
    "punctuation",
    "reorder_tokens",
    "drop_token",
    "initial",
    "whitespace",
]

LEGAL_FORMS: dict[str, str] = {
    "Public Joint Stock Company": "PJSC",
    "Open Joint Stock Company": "OJSC",
    "Closed Joint Stock Company": "CJSC",
    "Joint Stock Company": "JSC",
    "Public Limited Company": "PLC",
    "Limited Liability Company": "LLC",
    "Publichnoe Aktsionernoe Obshchestvo": "PAO",
    "Otkrytoe Aktsionernoe Obshchestvo": "OAO",
    "Zakrytoe Aktsionernoe Obshchestvo": "ZAO",
    "Aktsionernoe Obshchestvo": "AO",
    "Aktiengesellschaft": "AG",
    "Corporation": "Corp",
    "Limited": "Ltd",
    "Company": "Co",
}
"""Legal forms and their abbreviations, longest first so `Joint Stock Company` never matches inside `Public ...`."""
_FORM_PATTERN = re.compile(
    r"(?<!\w)(?:"
    + "|".join(r"[\s-]+".join(map(re.escape, form.split())) for form in [*LEGAL_FORMS, *LEGAL_FORMS.values()])
    + r")\.?(?!\w)",
    re.IGNORECASE,
)
_ABBREVIATIONS = {abbreviation.casefold(): full for full, abbreviation in LEGAL_FORMS.items()}
_FULL_FORMS = {full.casefold(): abbreviation for full, abbreviation in LEGAL_FORMS.items()}
_FILLERS = frozenset({"of", "the", "and", "for"})
_TYPOS = ("substitution", "transposition", "deletion", "insertion")
MAX_OPERATIONS = 2
_ATTEMPTS = 1000


@dataclass(frozen=True)
class Fuzz:
    base: Name
    operations: tuple[FuzzOperation, ...]
    """In the order applied."""
    rendered: str


def fuzz(rng: random.Random, entity: Entity) -> Fuzz:
    """Redraw base and operations from `rng` until the result keeps to the budget (spec 7.5, 7.6): at most two
    distinct operations (so at most one typo), Jaro-Winkler at least 0.85 to the base, at most 140 characters, and
    not a listed name even case-insensitively (a case change is not a fuzz)."""
    bases = [name for name in candidate_names(entity) if name.script == "latin"]
    listed = {name.value.casefold() for name in entity.names}
    operations = [op for op, types in OPERATIONS.items() if entity.entity_type in types]
    for _ in range(_ATTEMPTS):
        base = rng.choice(bases)
        drawn = rng.sample(operations, rng.randint(1, MAX_OPERATIONS))
        if {"abbreviate_legal_form", "expand_legal_form"} <= set(drawn):
            continue  # one would undo the other
        drawn.sort(key=lambda op: op == "whitespace")  # last, so no later operation re-joins the tokens
        value: str | None = base.value
        for op in drawn:
            value = apply_operation(op, value, entity.entity_type, rng)
            if value is None:
                break
        if (
            value is not None
            and len(value) <= MAX_NAME_LENGTH
            and value.casefold() not in listed
            and JaroWinkler.normalized_similarity(value, base.value) >= FUZZ_THRESHOLD
        ):
            return Fuzz(base, tuple(drawn), value)
    msg = f"no fuzz of {entity.id} keeps to the budget"
    raise RuntimeError(msg)


def apply_operation(operation: FuzzOperation, value: str, entity_type: EntityType, rng: random.Random) -> str | None:
    """`value` altered by one operation, or None when it does not apply to this name or Entity Type."""
    if entity_type not in OPERATIONS[operation]:
        return None
    result = _OPERATION_FUNCTIONS[operation](value, rng, entity_type)
    return result if result and result != value else None


def _typo(value: str, rng: random.Random, _: EntityType) -> str | None:
    """One substitution, transposition, deletion or insertion, never in a token's first two characters."""
    kind = rng.choice(_TYPOS)
    spots: list[tuple[int, bool]] = []  # (index into value, token in capitals)
    for token in re.finditer(r"\S+", value):
        start, end, upper = token.start(), token.end(), token[0].isupper()
        match kind:
            case "substitution":
                spots += [(i, upper) for i in range(start + 2, end) if value[i].isalpha()]
            case "transposition":
                spots += [(i, upper) for i in range(start + 2, end - 1) if value[i].lower() != value[i + 1].lower()]
            case "deletion":
                spots += [(i, upper) for i in range(start + 2, end)]
            case _:
                spots += [(i, upper) for i in range(start + 2, end + 1)]
    if not spots:
        return None
    i, upper = rng.choice(spots)
    letter = rng.choice([c for c in string.ascii_lowercase if c != value[i : i + 1].lower()])
    letter = letter.upper() if upper else letter
    match kind:
        case "substitution":
            return value[:i] + letter + value[i + 1 :]
        case "transposition":
            return value[:i] + value[i + 1] + value[i] + value[i + 2 :]
        case "deletion":
            return value[:i] + value[i + 1 :]
        case _:
            return value[:i] + letter + value[i:]


def _forms(value: str) -> list[re.Match[str]]:
    return list(_FORM_PATTERN.finditer(value))


def _key(form: str) -> str:
    return " ".join(re.split(r"[\s-]+", form.rstrip("."))).casefold()


def _cased(form: str, value: str) -> str:
    return form.upper() if value.isupper() else form


def _tidy(value: str) -> str:
    """After a form is cut out: no empty brackets, doubled spaces or dangling commas."""
    value = re.sub(r"\(\s*\)", "", value)
    value = re.sub(r"\s+([,)])", r"\1", re.sub(r"\(\s+", "(", value))
    return re.sub(r"\s{2,}", " ", value).strip(" ,")


def _drop_legal_form(value: str, rng: random.Random, _: EntityType) -> str | None:
    forms = _forms(value)
    if not forms:
        return None
    form = rng.choice(forms)
    return _tidy(value[: form.start()] + value[form.end() :])


def _replace_form(value: str, rng: random.Random, table: dict[str, str]) -> str | None:
    forms = [form for form in _forms(value) if _key(form[0]) in table]
    if not forms:
        return None
    form = rng.choice(forms)
    return value[: form.start()] + _cased(table[_key(form[0])], value) + value[form.end() :]


def _abbreviate_legal_form(value: str, rng: random.Random, _: EntityType) -> str | None:
    return _replace_form(value, rng, _FULL_FORMS)


def _expand_legal_form(value: str, rng: random.Random, _: EntityType) -> str | None:
    return _replace_form(value, rng, _ABBREVIATIONS)


def _strip_diacritics(value: str) -> str:
    return unicodedata.normalize(
        "NFC", "".join(c for c in unicodedata.normalize("NFD", value) if not unicodedata.combining(c))
    )


def _punctuation(value: str, rng: random.Random, _: EntityType) -> str | None:
    """Hyphens to spaces or one space to a hyphen; or quotes, brackets, dots or diacritics dropped."""
    spaces = [m.start() for m in re.finditer(" ", value)]
    edits: list[Callable[[], str]] = [
        lambda: value.replace("-", " "),
        lambda: re.sub(r"[\"'«»“”„\u2018\u2019]", "", value),
        lambda: re.sub(r"[()\[\]{}]", "", value),
        lambda: value.replace(".", ""),
        lambda: _strip_diacritics(value),
    ]
    if spaces:
        at = rng.choice(spaces)
        edits.append(lambda: value[:at] + "-" + value[at + 1 :])
    changed = [result for edit in edits if (result := _tidy(edit())) != value]
    return rng.choice(changed) if changed else None


def _reorder_tokens(value: str, _: random.Random, entity_type: EntityType) -> str | None:
    """An Individual's surname first; a Legal Entity's leading or trailing legal form moved to the other end."""
    tokens = value.split()
    if len(tokens) < 2:
        return None
    if entity_type == "individual":
        return " ".join([tokens[-1], *tokens[:-1]])
    forms = _forms(value)
    if forms and forms[0].start() == 0:
        return f"{value[forms[0].end() :].strip()} {forms[0][0]}"
    if forms and forms[-1].end() == len(value):
        return f"{forms[-1][0]} {value[: forms[-1].start()].strip()}"
    return None


def _drop_token(value: str, rng: random.Random, entity_type: EntityType) -> str | None:
    """A filler word such as "of", or an Individual's middle name or patronymic; never the first or last token."""
    tokens = value.split()
    inner = range(1, len(tokens) - 1)
    droppable = [i for i in inner if entity_type == "individual" or tokens[i].casefold() in _FILLERS]
    if not droppable:
        return None
    drop = rng.choice(droppable)
    return " ".join(token for i, token in enumerate(tokens) if i != drop)


def _initial(value: str, _: random.Random, __: EntityType) -> str | None:
    tokens = value.split()
    if len(tokens) < 2 or len(tokens[0]) < 2 or not tokens[0][0].isalpha():
        return None
    return " ".join([f"{tokens[0][0]}.", *tokens[1:]])


def _whitespace(value: str, rng: random.Random, _: EntityType) -> str | None:
    """A doubled space or a trailing one."""
    spaces = [m.start() for m in re.finditer(" ", value)]
    if spaces and rng.random() < 0.5:
        at = rng.choice(spaces)
        return value[:at] + " " + value[at:]
    return value + " "


_EVERY_TYPE: frozenset[EntityType] = frozenset({"individual", *LEGAL_ENTITIES})
OPERATIONS: dict[FuzzOperation, frozenset[EntityType]] = {
    "typo": _EVERY_TYPE,
    "drop_legal_form": LEGAL_ENTITIES,
    "abbreviate_legal_form": LEGAL_ENTITIES,
    "expand_legal_form": LEGAL_ENTITIES,
    "punctuation": _EVERY_TYPE,
    "reorder_tokens": _EVERY_TYPE,
    "drop_token": _EVERY_TYPE,
    "initial": frozenset({"individual"}),
    "whitespace": _EVERY_TYPE,
}
"""The operation catalogue and who each applies to (spec 7.5), in draw order: the order feeds the RNG."""
_OPERATION_FUNCTIONS: dict[FuzzOperation, Callable[[str, random.Random, EntityType], str | None]] = {
    "typo": _typo,
    "drop_legal_form": _drop_legal_form,
    "abbreviate_legal_form": _abbreviate_legal_form,
    "expand_legal_form": _expand_legal_form,
    "punctuation": _punctuation,
    "reorder_tokens": _reorder_tokens,
    "drop_token": _drop_token,
    "initial": _initial,
    "whitespace": _whitespace,
}
