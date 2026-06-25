from typing import Literal

from pydantic import BaseModel


class CreatePositionRequest(BaseModel):
    symbol: str
    market: str
    name: str | None = None
    kind: Literal["owned", "watching"] = "owned"
    qty: float | None = None
    cost_basis: float | None = None


class PositionResponse(BaseModel):
    id: str
    symbol: str
    market: str
    name: str | None
    kind: str
    qty: float | None
    cost_basis: float | None
