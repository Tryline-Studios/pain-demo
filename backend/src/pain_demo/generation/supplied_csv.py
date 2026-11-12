"""Supplied Data as a flat CSV (spec 5.6): one row per transaction, columns are the model's dotted field paths.

The CSV only reshapes cells into the nested `payment` and `transactions[]` of the JSON request; the Supplied Data
model in `supplied.py` validates them. An empty cell is absent, so a CSV cannot leave an optional element out.
"""

import csv
import io
from collections.abc import Iterator
from types import UnionType
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel

from pain_demo.generation.supplied import Location, SuppliedPayment, SuppliedTransaction

PAYMENT = "payment"
ROOT = "supplied_data"


class CsvInvalid(Exception):
    """Errors in Pydantic's shape at `supplied_data[<row>].<column>`, rows numbered from 1 like transactions."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors


def _error(location: Location, msg: str) -> dict[str, Any]:
    return {"loc": (ROOT, *location), "msg": msg, "type": "value_error"}


def _kind(annotation: Any) -> Any:
    """A field's model class, `list` with its item type, or None for a value."""
    if get_origin(annotation) is list:
        return list, get_args(annotation)[0]
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    if get_origin(annotation) in (Union, UnionType):
        return next((kind for arg in get_args(annotation) if (kind := _kind(arg)) is not None), None)
    return None


def _is_column(parts: list[str], annotation: Any) -> bool:
    match _kind(annotation):
        case None:
            return not parts
        case (_, item):
            return bool(parts) and parts[0].isdigit() and str(int(parts[0])) == parts[0] and _is_column(parts[1:], item)
        case model:
            return (
                bool(parts)
                and parts[0] in model.model_fields
                and _is_column(parts[1:], model.model_fields[parts[0]].annotation)
            )


def _paths(annotation: Any, path: str) -> Iterator[str]:
    match _kind(annotation):
        case None:
            yield path
        case (_, item):
            yield from _paths(item, f"{path}.0")
        case model:
            for name, field in model.model_fields.items():
                yield from _paths(field.annotation, f"{path}.{name}" if path else name)


def columns() -> list[str]:
    """The header template: every column, each list at position 0 (later positions are `.1`, `.2`, ...)."""
    return [*_paths(SuppliedPayment, PAYMENT), *_paths(SuppliedTransaction, "")]


def _set(tree: dict, parts: list[str], value: str) -> None:
    keys = [int(part) if part.isdigit() else part for part in parts]
    for key in keys[:-1]:
        tree = tree.setdefault(key, {})
    tree[keys[-1]] = value


def _nest(tree: dict, row: int, path: str = "") -> Any:
    """Dicts keyed by list positions become lists; positions must run from 0 without gaps."""
    nested = {
        key: _nest(value, row, f"{path}.{key}" if path else str(key)) if isinstance(value, dict) else value
        for key, value in tree.items()
    }
    if nested and all(isinstance(key, int) for key in nested):
        if sorted(nested) != list(range(len(nested))):
            raise CsvInvalid([_error((row, path), "list positions must run 0, 1, 2, ... without gaps")])
        return [nested[i] for i in range(len(nested))]
    return nested


def parse(content: bytes) -> dict[str, Any]:
    """The `payment` and `transactions` a request carries for this CSV; `CsvInvalid` names the row and column."""
    try:
        reader = csv.reader(io.StringIO(content.decode("utf-8-sig"), newline=""))
        header = next(reader, [])
        rows = [row for row in reader if any(cell.strip() for cell in row)]
    except (UnicodeDecodeError, csv.Error) as error:
        raise CsvInvalid([_error((), f"not a UTF-8 CSV: {error}")]) from error
    errors = [
        _error((column,), "unknown column; columns are field paths such as creditor.name or intermediary_agents.0.bic")
        for column in header
        if not (
            _is_column(column.split(".")[1:], SuppliedPayment)
            if column.startswith(f"{PAYMENT}.")
            else _is_column(column.split("."), SuppliedTransaction)
        )
    ]
    errors += [_error((column,), "duplicate column") for i, column in enumerate(header) if column in header[:i]]
    errors += [
        _error((n,), "more cells than the header has columns")
        for n, row in enumerate(rows, 1)
        if len(row) > len(header)
    ]
    if errors:
        raise CsvInvalid(errors)

    payment: dict = {}
    transactions = []
    row_one = dict(zip(header, rows[0], strict=False)) if rows else {}
    for number, row in enumerate(rows, 1):
        transaction: dict = {}
        for column, cell in zip(header, row, strict=False):
            if not cell:
                continue
            if column.startswith(f"{PAYMENT}."):
                if number == 1:
                    _set(payment, column.split(".")[1:], cell)
                elif cell != row_one.get(column, ""):
                    errors.append(
                        _error((number, column), "payment fields come from the first row; repeat it or leave it blank")
                    )
            else:
                _set(transaction, column.split("."), cell)
        transactions.append(_nest(transaction, number))
    if errors:
        raise CsvInvalid(errors)
    return {**({PAYMENT: _nest(payment, 1, PAYMENT)} if payment else {}), "transactions": transactions}


def locate(location: Location) -> Location:
    """A request location in CSV terms: `transactions[0].creditor.name` is row 1, column `creditor.name`."""
    match location:
        case ("body", *rest):
            return ("body", *locate(tuple(rest)))
        case ("payment", *rest):
            return (ROOT, 1, ".".join(map(str, (PAYMENT, *rest))))
        case ("transactions", int(index), *rest):
            return (ROOT, index + 1, *([".".join(map(str, rest))] if rest else []))
        case ("transactions",):
            return (ROOT,)
    return location
