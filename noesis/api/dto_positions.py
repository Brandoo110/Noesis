from typing import Literal

from pydantic import BaseModel, model_validator


class ResolvePositionRequest(BaseModel):
    symbol: str | None = None
    market: str
    name: str | None = None
    kind: Literal["owned", "watching"] = "owned"

    @model_validator(mode="after")
    def require_symbol_or_name(self) -> "ResolvePositionRequest":
        symbol = self.symbol.strip() if self.symbol is not None else ""
        name = self.name.strip() if self.name is not None else ""
        if not symbol and not name:
            raise ValueError("symbol or name is required")
        return self


class ResolvePositionResponse(BaseModel):
    status: Literal["resolved", "unresolved"]
    name: str | None
    symbol: str | None
    market: str
    node_type: str | None
    existing_position_id: str | None
    existing_position_label: str | None
