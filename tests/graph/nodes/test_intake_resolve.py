from dataclasses import dataclass

from noesis.db.models import EntityRow
from noesis.graph.nodes.intake_resolve import intake_resolve
from noesis.graph.schemas import PositionInput, ResolvedEntity
from noesis.graph.state import GraphDeps, ResearchState
from noesis.tools.llm.fake import FakeLLMRouter
from noesis.tools.llm.router import LLMRole


NOW = "2026-06-26T00:00:00Z"


class FakeEntitiesRepo:
    def __init__(self, existing: EntityRow | None = None) -> None:
        self.existing = existing
        self.upserted: list[EntityRow] = []

    def find_by_symbol(self, market: str, symbol: str) -> EntityRow | None:
        return self.existing

    def upsert(self, row: EntityRow) -> EntityRow:
        self.upserted.append(row)
        return row


@dataclass
class FakeRepos:
    entities: FakeEntitiesRepo


def make_deps(entities: FakeEntitiesRepo, llm: FakeLLMRouter) -> GraphDeps:
    return GraphDeps(
        repos=FakeRepos(entities=entities),
        search=object(),
        retriever=object(),
        llm=llm,
        now=lambda: NOW,
    )


def make_entity_row() -> EntityRow:
    return EntityRow(
        id="entity-aapl",
        node_type="company",
        name="Apple Inc.",
        aliases_json='["AAPL"]',
        identifiers_json='{"symbol": "AAPL"}',
        market="US",
        created_at=NOW,
        updated_at=NOW,
    )


def test_intake_resolve_reuses_existing_entity() -> None:
    state: ResearchState = {
        "raw_input": PositionInput(symbol="AAPL", market="US", name="Apple"),
        "degraded": [],
    }
    deps = make_deps(
        FakeEntitiesRepo(existing=make_entity_row()),
        FakeLLMRouter(available_roles=set()),
    )

    update = intake_resolve(state, deps)

    assert update["entity_id"] == "entity-aapl"
    assert update["resolved_entity"] == ResolvedEntity(
        entity_id="entity-aapl",
        node_type="company",
        name="Apple Inc.",
        aliases=["AAPL"],
        identifiers={"symbol": "AAPL"},
        market="US",
    )
    assert update["degraded"] == []


def test_intake_resolve_upserts_llm_resolved_entity() -> None:
    state: ResearchState = {
        "raw_input": PositionInput(symbol="MSFT", market="US", name="Microsoft"),
        "degraded": [],
    }
    entities = FakeEntitiesRepo()
    deps = make_deps(
        entities,
        FakeLLMRouter(
            json_by_role={
                LLMRole.LIGHT: {
                    "entity_id": "entity-msft",
                    "node_type": "company",
                    "name": "Microsoft Corp.",
                    "aliases": ["MSFT"],
                    "identifiers": {"symbol": "MSFT"},
                    "market": "US",
                }
            }
        ),
    )

    update = intake_resolve(state, deps)

    assert update["entity_id"] == "entity-msft"
    assert entities.upserted[0].id == "entity-msft"
    assert update["resolved_entity"].name == "Microsoft Corp."


def test_intake_resolve_degrades_when_light_llm_unavailable() -> None:
    state: ResearchState = {
        "raw_input": PositionInput(symbol="TSLA", market="US"),
        "degraded": [],
    }
    entities = FakeEntitiesRepo()
    deps = make_deps(entities, FakeLLMRouter(available_roles=set()))

    update = intake_resolve(state, deps)

    assert update["entity_id"] == "entity-us-tsla"
    assert update["resolved_entity"].name == "TSLA"
    assert update["degraded"][0].node_name == "intake_resolve"
    assert update["degraded"][0].fallback_used == "raw_symbol_entity"
