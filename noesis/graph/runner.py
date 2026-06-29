import logging
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from langgraph.types import Command

from noesis.db.connection import with_tx
from noesis.db.models import EntityRow, RunRow
from noesis.graph.build_graph import (
    build_expand_graph,
    build_seed_graph,
    make_sqlite_checkpointer,
)
from noesis.graph.errors import ResearchNodeError
from noesis.graph.runtime import RepoRuntime
from noesis.graph.schemas import (
    ConfirmationResult,
    EvidenceRecord,
    IntelItemDraft,
    PositionInput,
    ResolvedEntity,
    ThesisDraft,
)
from noesis.graph.snapshots import get_run_snapshot
from noesis.graph.state import GraphDeps, ResearchState
from noesis.graph.tracing import trace_node
from noesis.tools.llm.router import LLMRouter
from noesis.tools.retrieval.store import EvidenceRetriever
from noesis.tools.search.base import SearchAdapter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunHandle:
    run_id: str
    status: str
    thesis_id: str | None = None
    created: bool = False


@dataclass(frozen=True)
class RunSnapshot:
    run_id: str
    status: str
    thesis_id: str | None
    thesis_status: str | None
    resolved_entity: ResolvedEntity | None
    evidences: list[EvidenceRecord]
    intel_items: list[IntelItemDraft]
    thesis_draft: ThesisDraft | None


def build_graph_deps(
    *,
    conn: sqlite3.Connection,
    checkpoint_conn: sqlite3.Connection,
    chroma_dir: str,
    search: SearchAdapter,
    llm: LLMRouter,
    now: Callable[[], str],
) -> GraphDeps:
    return GraphDeps(
        repos=RepoRuntime(conn),
        search=search,
        retriever=EvidenceRetriever(chroma_dir, lambda: conn),
        llm=llm,
        now=now,
        checkpointer=make_sqlite_checkpointer(checkpoint_conn),
    )


def start_run(position_id: str, deps: GraphDeps) -> RunHandle:
    handle = create_seed_run(position_id, deps)
    if handle.created:
        execute_seed_run(handle.run_id, deps)
    return _handle(handle.run_id, deps)


def create_seed_run(position_id: str, deps: GraphDeps) -> RunHandle:
    position = deps.repos.positions.get(position_id)
    if position is None:
        raise ResearchNodeError("position not found", reason="position_not_found")
    running = deps.repos.runs.latest_seed_for_position(position_id)
    if running is not None and running.status == "running":
        return _handle(running.id, deps, created=False)
    run_id = f"run-{uuid4().hex}"
    _insert_run(run_id, position_id, deps)
    return _handle(run_id, deps, created=True)


def execute_seed_run(run_id: str, deps: GraphDeps) -> None:
    row = deps.repos.runs.get(run_id)
    if row is None:
        raise ResearchNodeError("run not found", reason="run_not_found")
    if row.node_kind != "seed":
        raise ResearchNodeError("run is not a seed run", reason="invalid_run_kind")
    if row.status != "running":
        return
    position = deps.repos.positions.get(row.position_id)
    if position is None:
        _set_run_failed(run_id, deps)
        raise ResearchNodeError("position not found", reason="position_not_found")
    state: ResearchState = {
        "run_id": run_id,
        "position_id": row.position_id,
        "node_kind": "seed",
        "raw_input": PositionInput(
            symbol=position.symbol or None,
            market=position.market,
            name=position.name,
            kind=position.kind,
            qty=position.qty,
            cost_basis=position.cost_basis,
        ),
        "degraded": [],
    }
    try:
        _graph(deps).invoke(state, _config(run_id))
    except ResearchNodeError:
        _set_run_failed(run_id, deps)
    except Exception:
        logger.exception("seed run failed unexpectedly", extra={"run_id": run_id})
        _set_run_failed(run_id, deps)


def resume_run(
    run_id: str, confirmation: ConfirmationResult, deps: GraphDeps
) -> RunHandle:
    try:
        _graph(deps).invoke(
            Command(resume=confirmation.model_dump(mode="json")),
            _config(run_id),
        )
    except ResearchNodeError:
        _set_run_failed(run_id, deps)
    except Exception:
        logger.exception("resume run failed unexpectedly", extra={"run_id": run_id})
        _set_run_failed(run_id, deps)
    return _handle(run_id, deps)


def start_expand_run(entity_id: str, position_id: str, deps: GraphDeps) -> RunHandle:
    cached = deps.repos.node_expansions.get(entity_id)
    if cached is not None and cached.researched == 1:
        return RunHandle(run_id=cached.cached_run_id or "", status="cached")
    entity = deps.repos.entities.get(entity_id)
    if entity is None:
        raise ResearchNodeError("entity not found", reason="entity_not_found")
    run_id = f"run-{uuid4().hex}"
    _insert_expand_run(run_id, position_id, entity_id, deps)
    state: ResearchState = {
        "run_id": run_id,
        "position_id": position_id,
        "entity_id": entity_id,
        "node_kind": "expand",
        "raw_input": _position_input_from_entity(entity),
        "degraded": [],
    }
    try:
        _expand_graph(deps).invoke(state, _config(run_id))
    except ResearchNodeError:
        _set_run_failed(run_id, deps)
    except Exception:
        logger.exception("expand run failed unexpectedly", extra={"run_id": run_id})
        _set_run_failed(run_id, deps)
    return _handle(run_id, deps)


def _graph(deps: GraphDeps) -> object:
    if deps.checkpointer is None:
        raise ResearchNodeError("checkpointer is required", reason="missing_checkpointer")
    return build_seed_graph(
        deps,
        checkpointer=deps.checkpointer,
        node_wrapper=trace_node,
    )


def _expand_graph(deps: GraphDeps) -> object:
    if deps.checkpointer is None:
        raise ResearchNodeError("checkpointer is required", reason="missing_checkpointer")
    return build_expand_graph(
        deps,
        checkpointer=deps.checkpointer,
        node_wrapper=trace_node,
    )


def _insert_run(run_id: str, position_id: str, deps: GraphDeps) -> None:
    with with_tx(deps.repos.conn):
        deps.repos.runs.insert(
            RunRow(
                id=run_id,
                position_id=position_id,
                entity_id=None,
                node_kind="seed",
                status="running",
                started_at=deps.now(),
                ended_at=None,
                created_at=deps.now(),
            )
        )


def _insert_expand_run(
    run_id: str, position_id: str, entity_id: str, deps: GraphDeps
) -> None:
    with with_tx(deps.repos.conn):
        deps.repos.runs.insert(
            RunRow(
                id=run_id,
                position_id=position_id,
                entity_id=entity_id,
                node_kind="expand",
                status="running",
                started_at=deps.now(),
                ended_at=None,
                created_at=deps.now(),
            )
        )


def _position_input_from_entity(entity: EntityRow) -> PositionInput:
    identifiers = entity.identifiers()
    symbol = identifiers.get("symbol")
    return PositionInput(
        symbol=symbol,
        market=entity.market or "",
        name=entity.name,
        kind="watching",
    )


def _config(run_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": run_id}}


def _handle(run_id: str, deps: GraphDeps, *, created: bool = False) -> RunHandle:
    row = deps.repos.runs.get(run_id)
    if row is None:
        raise ResearchNodeError("run not found", reason="run_not_found")
    thesis_id = f"thesis-{run_id}"
    if row.status == "awaiting_confirmation":
        return RunHandle(
            run_id=run_id,
            status=row.status,
            thesis_id=thesis_id,
            created=created,
        )
    thesis = deps.repos.theses.get(thesis_id)
    return RunHandle(
        run_id=run_id,
        status=row.status,
        thesis_id=thesis_id if thesis is not None else None,
        created=created,
    )


def _set_run_failed(run_id: str, deps: GraphDeps) -> None:
    with with_tx(deps.repos.conn):
        deps.repos.runs.set_status(run_id, "failed", deps.now())
