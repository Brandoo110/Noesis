import sqlite3
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status

from noesis.api.deps import get_graph_deps
from noesis.api.dto import CreatePositionRequest, EntityNodeResponse, PositionResponse
from noesis.api.dto_positions import ResolvePositionRequest, ResolvePositionResponse
from noesis.api.position_rows import (
    dedupe_positions,
    display_position_label,
    display_position_name,
    position_label,
    preferred_position,
)
from noesis.db.connection import with_tx
from noesis.db.models import EntityRow, PositionRow, RunRow
from noesis.graph.nodes.intake_resolve import preview_resolve
from noesis.graph.runner import get_run_snapshot
from noesis.graph.schemas import PositionInput, ResolvedEntity
from noesis.graph.state import GraphDeps

router = APIRouter(prefix="/positions", tags=["positions"])
LOCAL_USER_ID = "local-user"


@router.post(
    "",
    response_model=PositionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_position(
    request: CreatePositionRequest,
    response: Response,
    deps: GraphDeps = Depends(get_graph_deps),
) -> PositionResponse:
    symbol = _normalize_symbol(request.symbol)
    market = request.market.strip().upper()
    name = _normalize_name(request.name)
    label = symbol or name or ""
    existing = deps.repos.positions.list_by_identity(
        LOCAL_USER_ID,
        label,
        market,
        request.kind,
    )
    if existing:
        response.status_code = status.HTTP_200_OK
        return _position_response(preferred_position(existing, deps), deps)

    now = deps.now()
    row = PositionRow(
        id=f"position-{uuid4().hex}",
        user_id=LOCAL_USER_ID,
        symbol=symbol,
        market=market,
        name=name,
        kind=request.kind,
        qty=request.qty,
        cost_basis=request.cost_basis,
        created_at=now,
        updated_at=now,
    )
    with with_tx(deps.repos.conn):
        deps.repos.positions.insert(row)
    return _position_response(row, deps)


@router.post("/resolve", response_model=ResolvePositionResponse)
def resolve_position(
    request: ResolvePositionRequest,
    deps: GraphDeps = Depends(get_graph_deps),
) -> ResolvePositionResponse:
    market = request.market.strip().upper()
    raw_input = PositionInput(
        symbol=_normalize_symbol(request.symbol) or None,
        market=market,
        name=_normalize_name(request.name),
        kind=request.kind,
    )
    resolved = preview_resolve(raw_input, deps)
    if resolved is None:
        return ResolvePositionResponse(
            status="unresolved",
            name=raw_input.name,
            symbol=raw_input.symbol,
            market=market,
            node_type=None,
            existing_position_id=None,
            existing_position_label=None,
        )
    symbol = resolved.identifiers.get("symbol")
    resolved_market = (resolved.market or market).strip().upper()
    existing = deps.repos.positions.list_by_identity(
        LOCAL_USER_ID,
        symbol or resolved.name,
        resolved_market,
        request.kind,
    )
    row = preferred_position(existing, deps) if existing else None
    return ResolvePositionResponse(
        status="resolved",
        name=resolved.name,
        symbol=symbol,
        market=resolved_market,
        node_type=resolved.node_type,
        existing_position_id=row.id if row is not None else None,
        existing_position_label=position_label(row) if row is not None else None,
    )


@router.get("", response_model=list[PositionResponse])
def list_positions(
    deps: GraphDeps = Depends(get_graph_deps),
) -> list[PositionResponse]:
    rows = deps.repos.positions.list_by_user(LOCAL_USER_ID)
    return [_position_response(row, deps) for row in dedupe_positions(rows, deps)]


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(
    position_id: str,
    deps: GraphDeps = Depends(get_graph_deps),
) -> Response:
    row = deps.repos.positions.get(position_id)
    if row is None or row.user_id != LOCAL_USER_ID:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="position not found")

    run_ids = deps.repos.runs.list_ids_by_position(position_id)
    now = deps.now()
    with with_tx(deps.repos.conn):
        _delete_position_artifacts(position_id, run_ids, now, deps.repos.conn)
        deleted = deps.repos.positions.delete_for_user(position_id, LOCAL_USER_ID)
        if deleted == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="position not found",
            )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _position_response(row: PositionRow, deps: GraphDeps) -> PositionResponse:
    latest_run = deps.repos.runs.latest_seed_for_position(row.id)
    latest_entity = _latest_run_entity_response(latest_run, deps)
    return PositionResponse(
        id=row.id,
        symbol=display_position_label(
            row,
            latest_entity.symbol if latest_entity is not None else None,
        ),
        market=row.market,
        name=display_position_name(
            row,
            latest_entity.name if latest_entity is not None else None,
        ),
        kind=row.kind,
        qty=row.qty,
        cost_basis=row.cost_basis,
        latest_run_id=latest_run.id if latest_run is not None else None,
        latest_run_status=latest_run.status if latest_run is not None else None,
        latest_run_entity=latest_entity,
    )


def _normalize_name(name: str | None) -> str | None:
    if name is None:
        return None
    normalized = name.strip()
    return normalized if normalized else None


def _normalize_symbol(symbol: str | None) -> str:
    if symbol is None:
        return ""
    return symbol.strip().upper()


def _latest_run_entity_response(
    latest_run: RunRow | None,
    deps: GraphDeps,
) -> EntityNodeResponse | None:
    if latest_run is None:
        return None
    entity = _entity_from_run_row(latest_run, deps)
    if entity is None:
        entity = _entity_from_run_snapshot(latest_run, deps)
    if entity is None:
        return None
    return EntityNodeResponse(
        id=entity.id,
        name=entity.name,
        node_type=entity.node_type,
        symbol=entity.identifiers().get("symbol"),
        market=entity.market,
    )


def _entity_from_run_row(latest_run: RunRow, deps: GraphDeps) -> EntityRow | None:
    if latest_run.entity_id is None:
        return None
    return deps.repos.entities.get(latest_run.entity_id)


def _entity_from_run_snapshot(
    latest_run: RunRow,
    deps: GraphDeps,
) -> EntityRow | None:
    try:
        snapshot = get_run_snapshot(latest_run.id, deps)
    except Exception:
        return None
    resolved = snapshot.resolved_entity
    if not isinstance(resolved, ResolvedEntity):
        return None
    return deps.repos.entities.get(resolved.entity_id)


def _delete_position_artifacts(
    position_id: str,
    run_ids: list[str],
    now: str,
    conn: sqlite3.Connection,
) -> None:
    conn.execute("DELETE FROM holding_relevances WHERE position_id = ?", (position_id,))
    if not run_ids:
        return

    _delete_assumptions_for_position_runs(position_id, run_ids, conn)
    for table in (
        "approvals",
        "node_traces",
        "tool_invocations",
        "source_documents",
        "intel_items",
        "graph_edges",
        "evidences",
    ):
        _delete_by_run_ids(table, run_ids, conn)
    _delete_theses_for_position_runs(position_id, run_ids, conn)
    _reset_cached_expansions(run_ids, now, conn)
    _delete_runs(run_ids, conn)
    _rebuild_evidences_fts(conn)


def _delete_assumptions_for_position_runs(
    position_id: str,
    run_ids: list[str],
    conn: sqlite3.Connection,
) -> None:
    placeholders = _placeholders(run_ids)
    conn.execute(
        f"""
        DELETE FROM thesis_assumptions
        WHERE thesis_id IN (
          SELECT id FROM theses
          WHERE position_id = ? OR run_id IN ({placeholders})
        )
        """,
        (position_id, *run_ids),
    )


def _delete_theses_for_position_runs(
    position_id: str,
    run_ids: list[str],
    conn: sqlite3.Connection,
) -> None:
    placeholders = _placeholders(run_ids)
    conn.execute(
        f"""
        DELETE FROM theses
        WHERE position_id = ? OR run_id IN ({placeholders})
        """,
        (position_id, *run_ids),
    )


def _delete_by_run_ids(
    table: str,
    run_ids: list[str],
    conn: sqlite3.Connection,
) -> None:
    placeholders = _placeholders(run_ids)
    conn.execute(
        f"DELETE FROM {table} WHERE run_id IN ({placeholders})",
        tuple(run_ids),
    )


def _delete_runs(run_ids: list[str], conn: sqlite3.Connection) -> None:
    placeholders = _placeholders(run_ids)
    conn.execute(
        f"DELETE FROM run_registry WHERE id IN ({placeholders})",
        tuple(run_ids),
    )


def _reset_cached_expansions(
    run_ids: list[str],
    now: str,
    conn: sqlite3.Connection,
) -> None:
    placeholders = _placeholders(run_ids)
    conn.execute(
        f"""
        UPDATE node_expansions
        SET researched = 0,
            researched_at = NULL,
            cached_run_id = NULL,
            updated_at = ?
        WHERE cached_run_id IN ({placeholders})
        """,
        (now, *run_ids),
    )


def _rebuild_evidences_fts(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO evidences_fts(evidences_fts) VALUES('delete-all')")
    conn.execute(
        """
        INSERT INTO evidences_fts(rowid, evidence_id, snippet, title)
        SELECT rowid, id, snippet, title FROM evidences
        """
    )


def _placeholders(values: list[str]) -> str:
    return ", ".join("?" for _ in values)
