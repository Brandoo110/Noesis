from sqlite3 import Row
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def row_to_model(row: Row | None, model: type[T]) -> T | None:
    if row is None:
        return None
    return model.model_validate(dict(row))


def rows_to_models(rows: list[Row], model: type[T]) -> list[T]:
    return [model.model_validate(dict(row)) for row in rows]
