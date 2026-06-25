from noesis.graph.schemas import IngestedDoc


class FakeSearchAdapter:
    def __init__(self, docs: list[IngestedDoc]) -> None:
        self.docs = docs

    def search(self, query: str, *, limit: int = 8) -> list[IngestedDoc]:
        return self.docs[:limit]
