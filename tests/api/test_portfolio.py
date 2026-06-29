import json

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import (
    EntityRow,
    GraphEdgeRow,
    NodeTraceRow,
    PositionRow,
    RunRow,
    ThesisRow,
)
from noesis.db.repos.entities_repo import EntitiesRepo
from noesis.db.repos.graph_edges_repo import GraphEdgesRepo
from noesis.db.repos.node_traces_repo import NodeTracesRepo
from noesis.db.repos.positions_repo import PositionsRepo
from noesis.db.repos.run_registry_repo import RunRegistryRepo
from noesis.db.repos.theses_repo import ThesesRepo
from tests.api.conftest import ApiTestContext, NOW


def test_portfolio_overlaps_returns_shared_segment(
    api_context: ApiTestContext,
) -> None:
    _seed_shared_overlap(api_context)

    response = api_context.client.get("/portfolio/overlaps")
    payload = response.json()

    assert response.status_code == 200
    assert payload == [
        {
            "segment_id": "segment-consumer",
            "segment_name": "Consumer Electronics",
            "node_type": "segment",
            "basis": "inferred",
            "positions": [
                {
                    "position_id": "position-aapl",
                    "symbol": "AAPL",
                    "entity_id": "entity-aapl",
                    "confidence": 0.9,
                },
                {
                    "position_id": "position-msft",
                    "symbol": "MSFT",
                    "entity_id": "entity-msft",
                    "confidence": 0.7,
                },
            ],
        }
    ]


def test_portfolio_overlaps_returns_empty_without_positions(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.get("/portfolio/overlaps")

    assert response.status_code == 200
    assert response.json() == []


def test_portfolio_overlaps_skips_unresearched_positions(
    api_context: ApiTestContext,
) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            PositionsRepo().insert(
                _position("position-aapl", "AAPL", "Apple"),
                conn=conn,
            )
    finally:
        conn.close()

    response = api_context.client.get("/portfolio/overlaps")

    assert response.status_code == 200
    assert response.json() == []


def test_portfolio_brief_returns_positions_theses_and_overlaps(
    api_context: ApiTestContext,
) -> None:
    _seed_shared_overlap(api_context)
    _seed_thesis(
        api_context,
        "thesis-aapl",
        "position-aapl",
        "AAPL thesis",
        "confirmed",
        run_id="run-aapl",
    )
    _seed_thesis(
        api_context,
        "thesis-msft",
        "position-msft",
        "MSFT thesis",
        "draft",
        run_id="run-msft",
    )

    response = api_context.client.get("/portfolio/brief")
    payload = response.json()

    assert response.status_code == 200
    assert payload == {
        "generated_at": NOW,
        "positions": [
            {
                "position_id": "position-aapl",
                "symbol": "AAPL",
                "name": "Apple",
                "thesis_summary": "AAPL thesis",
                "thesis_status": "confirmed",
            },
            {
                "position_id": "position-msft",
                "symbol": "MSFT",
                "name": "Microsoft",
                "thesis_summary": "MSFT thesis",
                "thesis_status": "draft",
            },
        ],
        "overlaps": [
            {
                "segment_id": "segment-consumer",
                "segment_name": "Consumer Electronics",
                "node_type": "segment",
                "basis": "inferred",
                "positions": [
                    {
                        "position_id": "position-aapl",
                        "symbol": "AAPL",
                        "entity_id": "entity-aapl",
                        "confidence": 0.9,
                    },
                    {
                        "position_id": "position-msft",
                        "symbol": "MSFT",
                        "entity_id": "entity-msft",
                        "confidence": 0.7,
                    },
                ],
            }
        ],
        "run_health": {
            "total_latest_runs": 2,
            "running": 0,
            "awaiting_confirmation": 0,
            "completed": 2,
            "failed": 0,
            "completed_without_thesis": 0,
            "degraded_runs": 0,
            "failed_runs": [],
            "degraded_reasons": [],
        },
    }


def test_portfolio_brief_returns_null_thesis_for_unresearched_position(
    api_context: ApiTestContext,
) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            PositionsRepo().insert(
                _position("position-sony", "SONY", "Sony"),
                conn=conn,
            )
    finally:
        conn.close()

    response = api_context.client.get("/portfolio/brief")
    payload = response.json()

    assert response.status_code == 200
    assert payload == {
        "generated_at": NOW,
        "positions": [
            {
                "position_id": "position-sony",
                "symbol": "SONY",
                "name": "Sony",
                "thesis_summary": None,
                "thesis_status": None,
            }
        ],
        "overlaps": [],
        "run_health": {
            "total_latest_runs": 0,
            "running": 0,
            "awaiting_confirmation": 0,
            "completed": 0,
            "failed": 0,
            "completed_without_thesis": 0,
            "degraded_runs": 0,
            "failed_runs": [],
            "degraded_reasons": [],
        },
    }


def test_portfolio_brief_collapses_duplicate_position_identity(
    api_context: ApiTestContext,
) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            positions = PositionsRepo()
            positions.insert(_position("position-aapl", "AAPL", "Apple"), conn=conn)
            positions.insert(
                _position("position-aapl-duplicate", "AAPL", "Apple duplicate"),
                conn=conn,
            )
            RunRegistryRepo().insert(
                _run("run-aapl", "position-aapl", "entity-aapl"),
                conn=conn,
            )
            ThesesRepo().insert(
                ThesisRow(
                    id="thesis-aapl",
                    position_id="position-aapl",
                    run_id="run-aapl",
                    summary="AAPL thesis",
                    status="confirmed",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                conn=conn,
            )
    finally:
        conn.close()

    response = api_context.client.get("/portfolio/brief")
    payload = response.json()

    assert response.status_code == 200
    assert payload["positions"] == [
        {
            "position_id": "position-aapl",
            "symbol": "AAPL",
            "name": "Apple",
            "thesis_summary": "AAPL thesis",
            "thesis_status": "confirmed",
        }
    ]
    assert payload["run_health"]["total_latest_runs"] == 1


def test_portfolio_brief_returns_empty_payload_without_positions(
    api_context: ApiTestContext,
) -> None:
    response = api_context.client.get("/portfolio/brief")

    assert response.status_code == 200
    assert response.json() == {
        "generated_at": NOW,
        "positions": [],
        "overlaps": [],
        "run_health": {
            "total_latest_runs": 0,
            "running": 0,
            "awaiting_confirmation": 0,
            "completed": 0,
            "failed": 0,
            "completed_without_thesis": 0,
            "degraded_runs": 0,
            "failed_runs": [],
            "degraded_reasons": [],
        },
    }


def test_portfolio_brief_classifies_latest_run_health(
    api_context: ApiTestContext,
) -> None:
    _seed_run_health_cases(api_context)

    response = api_context.client.get("/portfolio/brief")
    payload = response.json()

    assert response.status_code == 200
    assert payload["run_health"] == {
        "total_latest_runs": 3,
        "running": 0,
        "awaiting_confirmation": 0,
        "completed": 2,
        "failed": 1,
        "completed_without_thesis": 1,
        "degraded_runs": 1,
        "failed_runs": [
            {
                "position_id": "position-msft",
                "symbol": "MSFT",
                "run_id": "run-msft-failed",
                "status": "failed",
                "reason": "graph_wiring_failed",
            }
        ],
        "degraded_reasons": [
            {
                "reason": "no_intel_for_thesis",
                "count": 1,
            }
        ],
    }


def _seed_shared_overlap(api_context: ApiTestContext) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            positions = PositionsRepo()
            positions.insert(_position("position-aapl", "AAPL", "Apple"), conn=conn)
            positions.insert(_position("position-msft", "MSFT", "Microsoft"), conn=conn)

            entities = EntitiesRepo()
            entities.upsert(_entity("entity-aapl", "Apple Inc.", "AAPL"), conn=conn)
            entities.upsert(_entity("entity-msft", "Microsoft Corp.", "MSFT"), conn=conn)
            entities.upsert(
                _entity(
                    "segment-consumer",
                    "Consumer Electronics",
                    None,
                    node_type="segment",
                ),
                conn=conn,
            )

            runs = RunRegistryRepo()
            runs.insert(_run("run-aapl", "position-aapl", "entity-aapl"), conn=conn)
            runs.insert(_run("run-msft", "position-msft", "entity-msft"), conn=conn)

            GraphEdgesRepo().insert_many(
                [
                    _edge(
                        "edge-aapl-consumer",
                        "entity-aapl",
                        "segment-consumer",
                        basis="source_backed",
                        confidence=0.9,
                    ),
                    _edge(
                        "edge-msft-consumer",
                        "entity-msft",
                        "segment-consumer",
                        basis="inferred",
                        confidence=0.7,
                    ),
                ],
                conn=conn,
            )
    finally:
        conn.close()


def _seed_thesis(
    api_context: ApiTestContext,
    id: str,
    position_id: str,
    summary: str,
    status: str,
    *,
    run_id: str | None = None,
) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            ThesesRepo().insert(
                ThesisRow(
                    id=id,
                    position_id=position_id,
                    run_id=run_id or f"run-{id}",
                    summary=summary,
                    status=status,
                    created_at=NOW,
                    updated_at=NOW,
                ),
                conn=conn,
            )
    finally:
        conn.close()


def _seed_run_health_cases(api_context: ApiTestContext) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            positions = PositionsRepo()
            positions.insert(_position("position-aapl", "AAPL", "Apple"), conn=conn)
            positions.insert(_position("position-msft", "MSFT", "Microsoft"), conn=conn)
            positions.insert(_position("position-sony", "SONY", "Sony"), conn=conn)

            entities = EntitiesRepo()
            entities.upsert(_entity("entity-aapl", "Apple Inc.", "AAPL"), conn=conn)
            entities.upsert(_entity("entity-msft", "Microsoft Corp.", "MSFT"), conn=conn)
            entities.upsert(_entity("entity-sony", "Sony Group", "SONY"), conn=conn)

            runs = RunRegistryRepo()
            runs.insert(_run("run-aapl-ok", "position-aapl", "entity-aapl"), conn=conn)
            runs.insert(_run("run-sony-no-thesis", "position-sony", "entity-sony"), conn=conn)
            runs.insert(
                RunRow(
                    id="run-msft-failed",
                    position_id="position-msft",
                    entity_id="entity-msft",
                    node_kind="seed",
                    status="failed",
                    started_at=NOW,
                    ended_at=NOW,
                    created_at=NOW,
                ),
                conn=conn,
            )
            ThesesRepo().insert(
                ThesisRow(
                    id="thesis-aapl",
                    position_id="position-aapl",
                    run_id="run-aapl-ok",
                    summary="AAPL thesis",
                    status="confirmed",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                conn=conn,
            )
            traces = NodeTracesRepo()
            traces.insert(
                _trace(
                    "trace-sony-degraded",
                    "run-sony-no-thesis",
                    status="degraded",
                    reason="no_intel_for_thesis",
                    fallback_used="no_thesis_draft",
                ),
                conn=conn,
            )
            traces.insert(
                _trace(
                    "trace-msft-failed",
                    "run-msft-failed",
                    status="failed",
                    reason="graph_wiring_failed",
                    fallback_used=None,
                ),
                conn=conn,
            )
    finally:
        conn.close()


def _position(id: str, symbol: str, name: str) -> PositionRow:
    return PositionRow(
        id=id,
        user_id="local-user",
        symbol=symbol,
        market="US",
        name=name,
        kind="owned",
        qty=None,
        cost_basis=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _entity(
    id: str,
    name: str,
    symbol: str | None,
    *,
    node_type: str = "company",
) -> EntityRow:
    aliases = [] if symbol is None else [symbol]
    identifiers = {} if symbol is None else {"symbol": symbol}
    return EntityRow(
        id=id,
        node_type=node_type,
        name=name,
        aliases_json=json.dumps(aliases),
        identifiers_json=json.dumps(identifiers),
        market="US",
        created_at=NOW,
        updated_at=NOW,
    )


def _run(id: str, position_id: str, entity_id: str) -> RunRow:
    return RunRow(
        id=id,
        position_id=position_id,
        entity_id=entity_id,
        node_kind="seed",
        status="completed",
        started_at=NOW,
        ended_at=NOW,
        created_at=NOW,
    )


def _trace(
    id: str,
    run_id: str,
    *,
    status: str,
    reason: str | None,
    fallback_used: str | None,
) -> NodeTraceRow:
    return NodeTraceRow(
        id=id,
        run_id=run_id,
        node_name="thesis_draft",
        entity_id=None,
        inputs_ref=None,
        outputs_ref=None,
        status=status,
        reason=reason,
        fallback_used=fallback_used,
        model_id=None,
        evidence_ids_json=json.dumps([]),
        started_at=NOW,
        ended_at=NOW,
        created_at=NOW,
    )


def _edge(
    id: str,
    from_entity_id: str,
    to_entity_id: str,
    *,
    basis: str,
    confidence: float,
) -> GraphEdgeRow:
    return GraphEdgeRow(
        id=id,
        from_entity_id=from_entity_id,
        to_entity_id=to_entity_id,
        relation="belongs_to",
        basis=basis,
        confidence=confidence,
        evidence_ids_json=json.dumps([]),
        run_id="run-overlap",
        rationale="Portfolio overlap segment.",
        created_at=NOW,
    )
