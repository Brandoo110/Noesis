from noesis.graph.nodes.intake_resolve import preview_resolve
from noesis.graph.schemas import PositionInput
from noesis.tools.llm.fake import FakeLLMRouter
from noesis.tools.llm.router import LLMRole
from tests.graph.nodes.test_intake_resolve import (
    FakeEntitiesRepo,
    make_deps,
    make_entity_row,
)


def test_preview_resolve_returns_existing_entity_without_llm() -> None:
    entities = FakeEntitiesRepo(existing=make_entity_row())
    deps = make_deps(entities, FakeLLMRouter(available_roles=set()))

    resolved = preview_resolve(
        PositionInput(symbol="AAPL", market="US", name=None), deps
    )

    assert resolved is not None
    assert resolved.entity_id == "entity-aapl"
    assert resolved.name == "Apple Inc."
    assert entities.upserted == []


def test_preview_resolve_resolves_name_without_persisting() -> None:
    entities = FakeEntitiesRepo()
    deps = make_deps(
        entities,
        FakeLLMRouter(
            json_by_role={
                LLMRole.LIGHT: {
                    "entity_id": "entity-tsla",
                    "node_type": "company",
                    "name": "Tesla, Inc.",
                    "aliases": ["TSLA", "Tesla"],
                    "identifiers": {"ticker": "tsla"},
                    "market": "US",
                }
            }
        ),
    )

    resolved = preview_resolve(
        PositionInput(symbol=None, market="US", name="tesla"), deps
    )

    assert resolved is not None
    assert resolved.name == "Tesla, Inc."
    assert resolved.identifiers.get("symbol") == "TSLA"
    assert entities.upserted == []


def test_preview_resolve_returns_none_when_llm_unavailable() -> None:
    entities = FakeEntitiesRepo()
    deps = make_deps(entities, FakeLLMRouter(available_roles=set()))

    resolved = preview_resolve(
        PositionInput(symbol=None, market="US", name="somecorp"), deps
    )

    assert resolved is None


def test_preview_resolve_returns_none_when_llm_fails() -> None:
    entities = FakeEntitiesRepo()
    deps = make_deps(entities, FakeLLMRouter(text_by_role={LLMRole.LIGHT: "not-json"}))

    resolved = preview_resolve(
        PositionInput(symbol=None, market="US", name="somecorp"), deps
    )

    assert resolved is None
