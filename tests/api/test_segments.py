import json

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import EntityRow, GraphEdgeRow
from noesis.db.repos.entities_repo import EntitiesRepo
from noesis.db.repos.graph_edges_repo import GraphEdgesRepo
from tests.api.conftest import ApiTestContext, NOW


def test_segment_representatives_returns_companies_sorted_by_confidence(
    api_context: ApiTestContext,
) -> None:
    _seed_representative_graph(api_context)

    response = api_context.client.get("/segments/entity-segment-ai/representatives")
    payload = response.json()

    assert response.status_code == 200
    assert payload["segment_id"] == "entity-segment-ai"
    assert [item["symbol"] for item in payload["representatives"]] == [
        "ONE",
        "THREE",
        "TWO",
    ]


def test_segment_representatives_returns_empty_result(
    api_context: ApiTestContext,
) -> None:
    _seed_segment(api_context)

    response = api_context.client.get("/segments/entity-segment-ai/representatives")

    assert response.status_code == 200
    assert response.json()["representatives"] == []


def _seed_representative_graph(api_context: ApiTestContext) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            entities = EntitiesRepo()
            entities.upsert(_segment(), conn=conn)
            entities.upsert(_company("entity-company-one", "One Corp", "ONE"), conn=conn)
            entities.upsert(_company("entity-company-two", "Two Corp", "TWO"), conn=conn)
            entities.upsert(
                _company("entity-company-three", "Three Corp", "THREE"),
                conn=conn,
            )
            GraphEdgesRepo().insert_many(
                [
                    _edge("edge-one", "entity-company-one", 0.9),
                    _edge("edge-two", "entity-company-two", 0.6),
                    _edge("edge-three", "entity-company-three", 0.8),
                ],
                conn=conn,
            )
    finally:
        conn.close()


def _seed_segment(api_context: ApiTestContext) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            EntitiesRepo().upsert(_segment(), conn=conn)
    finally:
        conn.close()


def _segment() -> EntityRow:
    return EntityRow(
        id="entity-segment-ai",
        node_type="segment",
        name="AI accelerators",
        aliases_json=json.dumps([]),
        identifiers_json=json.dumps({}),
        market=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _company(id: str, name: str, symbol: str) -> EntityRow:
    return EntityRow(
        id=id,
        node_type="company",
        name=name,
        aliases_json=json.dumps([symbol]),
        identifiers_json=json.dumps({"symbol": symbol}),
        market="US",
        created_at=NOW,
        updated_at=NOW,
    )


def _edge(id: str, from_entity_id: str, confidence: float) -> GraphEdgeRow:
    return GraphEdgeRow(
        id=id,
        from_entity_id=from_entity_id,
        to_entity_id="entity-segment-ai",
        relation="belongs_to",
        basis="inferred",
        confidence=confidence,
        evidence_ids_json=json.dumps([]),
        run_id="run-1",
        rationale="Segment membership.",
        created_at=NOW,
    )
