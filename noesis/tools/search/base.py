from typing import Protocol

from noesis.graph.schemas import IngestedDoc


class SearchAdapter(Protocol):
    def search(self, query: str, *, limit: int = 8) -> list[IngestedDoc]: ...
