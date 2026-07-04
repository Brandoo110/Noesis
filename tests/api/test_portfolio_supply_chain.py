import json
import sqlite3

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import EntityRow, GraphEdgeRow, PositionRow, RunRow
from noesis.db.repos.entities_repo import EntitiesRepo
from noesis.db.repos.graph_edges_repo import GraphEdgesRepo
from noesis.db.repos.positions_repo import PositionsRepo
from noesis.db.repos.run_registry_repo import RunRegistryRepo
from tests.api.conftest import ApiTestContext, NOW


def test_portfolio_shared_suppliers_returns_shared_supplier_group(
    api_context: ApiTestContext,
) -> None:
    _seed_shared_supplier(api_context)

    response = api_context.client.get("/portfolio/shared-suppliers")

    assert response.status_code == 200
    assert response.json() == [
        {
            "supplier_id": "entity-tsmc",
            "supplier_name": "Taiwan Semiconductor",
            "node_type": "company",
            "basis": "inferred",
            "positions": [
                {
                    "position_id": "position-aapl",
                    "symbol": "AAPL",
                    "entity_id": "entity-aapl",
                    "confidence": 0.91,
                },
                {
                    "position_id": "position-msft",
                    "symbol": "MSFT",
                    "entity_id": "entity-msft",
                    "confidence": 0.62,
                },
            ],
        }
    ]


def test_portfolio_shared_suppliers_empty_without_supplier_edges(
    api_context: ApiTestContext,
) -> None:
    _seed_positions_without_supplier_edges(api_context)

    response = api_context.client.get("/portfolio/shared-suppliers")

    assert response.status_code == 200
    assert response.json() == []


def test_portfolio_correlation_returns_sparse_shared_supplier_cells(
    api_context: ApiTestContext,
) -> None:
    _seed_shared_supplier(api_context)

    response = api_context.client.get("/portfolio/correlation")

    assert response.status_code == 200
    assert response.json() == {
        "positions": [
            {"position_id": "position-aapl", "symbol": "AAPL", "label": "AAPL"},
            {"position_id": "position-msft", "symbol": "MSFT", "label": "MSFT"},
        ],
        "cells": [
            {
                "a_position_id": "position-aapl",
                "b_position_id": "position-msft",
                "shared_count": 1,
                "shared_suppliers": ["Taiwan Semiconductor"],
            }
        ],
    }


def test_portfolio_correlation_empty_without_expanded_supplier_edges(
    api_context: ApiTestContext,
) -> None:
    _seed_positions_without_supplier_edges(api_context)

    response = api_context.client.get("/portfolio/correlation")

    assert response.status_code == 200
    assert response.json()["cells"] == []


def _seed_shared_supplier(api_context: ApiTestContext) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            _seed_positions_and_runs(conn)
            entities = EntitiesRepo()
            entities.upsert(_entity("entity-tsmc", "Taiwan Semiconductor", "TSM"), conn=conn)
            GraphEdgesRepo().insert_many(
                [
                    _edge(
                        "edge-aapl-tsmc",
                        "entity-aapl",
                        "entity-tsmc",
                        basis="source_backed",
                        confidence=0.91,
                    ),
                    _edge(
                        "edge-msft-tsmc",
                        "entity-msft",
                        "entity-tsmc",
                        basis="inferred",
                        confidence=0.62,
                    ),
                ],
                conn=conn,
            )
    finally:
        conn.close()


def _seed_positions_without_supplier_edges(api_context: ApiTestContext) -> None:
    conn = connect(api_context.db_path)
    try:
        migrate(conn)
        with with_tx(conn):
            _seed_positions_and_runs(conn)
    finally:
        conn.close()


def _seed_positions_and_runs(conn: sqlite3.Connection) -> None:
    positions = PositionsRepo()
    positions.insert(_position("position-aapl", "AAPL", "Apple"), conn=conn)
    positions.insert(_position("position-msft", "", "Microsoft"), conn=conn)

    entities = EntitiesRepo()
    entities.upsert(_entity("entity-aapl", "Apple Inc.", "AAPL"), conn=conn)
    entities.upsert(_entity("entity-msft", "Microsoft Corp.", "MSFT"), conn=conn)

    runs = RunRegistryRepo()
    runs.insert(_run("run-aapl", "position-aapl", "entity-aapl"), conn=conn)
    runs.insert(_run("run-msft", "position-msft", "entity-msft"), conn=conn)


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


def _entity(id: str, name: str, symbol: str) -> EntityRow:
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
        relation="supplier",
        basis=basis,
        confidence=confidence,
        evidence_ids_json=json.dumps([]),
        run_id="run-supplier",
        rationale="Shared supplier.",
        created_at=NOW,
    )
