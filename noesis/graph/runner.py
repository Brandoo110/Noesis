import json
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from uuid import uuid4

from langgraph.errors import GraphBubbleUp
from langgraph.types import Command

from noesis.db.connection import with_tx
from noesis.db.models import NodeTraceRow, RunRow
from noesis.graph.build_graph import NodeFn, build_seed_graph, make_sqlite_checkpointer
from noesis.graph.errors import ResearchNodeError
from noesis.graph.runtime import RepoRuntime
from noesis.graph.schemas import (
    ConfirmationResult,
    DegradeNote,
    EvidenceRecord,
    IntelItemDraft,
    PositionInput,
    ThesisDraft,
)
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate
from noesis.tools.llm.router import LLMRouter
from noesis.tools.retrieval.store import EvidenceRetriever
from noesis.tools.search.base import SearchAdapter


@dataclass(frozen=True)
class RunHandle:
    run_id: str
    status: str
    thesis_id: str | None = None


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
    run_id = f"run-{uuid4().hex}"
    position = deps.repos.positions.get(position_id)
    if position is None:
        raise ResearchNodeError("position not found", reason="position_not_found")
    _insert_run(run_id, position_id, deps)
    state: ResearchState = {
        "run_id": run_id,
        "position_id": position_id,
        "node_kind": "seed",
        "raw_input": PositionInput(
            symbol=position.symbol,
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
    return _handle(run_id, deps)


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
    return _handle(run_id, deps)


def _graph(deps: GraphDeps) -> object:
    if deps.checkpointer is None:
        raise ResearchNodeError("checkpointer is required", reason="missing_checkpointer")
    return build_seed_graph(
        deps,
        checkpointer=deps.checkpointer,
        node_wrapper=_trace_node,
    )


def _trace_node(node_name: str, node_fn: NodeFn, deps: GraphDeps) -> Callable[[ResearchState], ResearchStateUpdate]:
    def run_node(state: ResearchState) -> ResearchStateUpdate:
        run_id = state.get("run_id") or "unknown-run"
        started_at = deps.now()
        _insert_trace(node_name, run_id, "started", started_at, None, state, deps)
        before_degraded = len(state.get("degraded", []))
        try:
            update = node_fn(state, deps)
        except GraphBubbleUp:
            _insert_trace(node_name, run_id, "success", started_at, deps.now(), state, deps)
            raise
        except Exception as exc:
            deps.repos.conn.rollback()
            _insert_trace(
                node_name,
                run_id,
                "failed",
                started_at,
                deps.now(),
                state,
                deps,
                reason=str(exc),
            )
            raise ResearchNodeError(
                f"{node_name} failed",
                reason="node_failed",
            ) from exc
        combined: ResearchState = {**state, **update}
        new_degraded = combined.get("degraded", [])[before_degraded:]
        status = "degraded" if new_degraded else "success"
        note = new_degraded[-1] if new_degraded else None
        _insert_trace(
            node_name,
            run_id,
            status,
            started_at,
            deps.now(),
            combined,
            deps,
            reason=note.reason if note else None,
            fallback_used=note.fallback_used if note else None,
        )
        return update

    return run_node


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


def _insert_trace(
    node_name: str,
    run_id: str,
    status: str,
    started_at: str,
    ended_at: str | None,
    state: ResearchState,
    deps: GraphDeps,
    *,
    reason: str | None = None,
    fallback_used: str | None = None,
) -> None:
    with with_tx(deps.repos.conn):
        deps.repos.traces.insert(
            NodeTraceRow(
                id=f"trace-{uuid4().hex}",
                run_id=run_id,
                node_name=node_name,
                entity_id=state.get("entity_id"),
                inputs_ref="state",
                outputs_ref=status,
                status=status,
                reason=reason,
                fallback_used=fallback_used,
                model_id=None,
                evidence_ids_json=_evidence_ids_json(state),
                started_at=started_at,
                ended_at=ended_at,
                created_at=deps.now(),
            )
        )


def _evidence_ids_json(state: Mapping[str, object]) -> str | None:
    ids: set[str] = set()
    for evidence in _typed_list(state.get("evidences"), EvidenceRecord):
        ids.add(evidence.id)
    for item in _typed_list(state.get("intel_items"), IntelItemDraft):
        ids.update(item.evidence_ids)
    thesis = state.get("thesis_draft")
    if isinstance(thesis, ThesisDraft):
        for assumption in thesis.assumptions:
            ids.update(assumption.evidence_ids)
    return json.dumps(sorted(ids)) if ids else None


def _typed_list(value: object, item_type: type) -> list:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, item_type)]


def _config(run_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": run_id}}


def _handle(run_id: str, deps: GraphDeps) -> RunHandle:
    row = deps.repos.runs.get(run_id)
    if row is None:
        raise ResearchNodeError("run not found", reason="run_not_found")
    thesis_id = f"thesis-{run_id}"
    if row.status == "awaiting_confirmation":
        return RunHandle(run_id=run_id, status=row.status, thesis_id=thesis_id)
    thesis = deps.repos.theses.get(thesis_id)
    return RunHandle(
        run_id=run_id,
        status=row.status,
        thesis_id=thesis_id if thesis is not None else None,
    )


def _set_run_failed(run_id: str, deps: GraphDeps) -> None:
    with with_tx(deps.repos.conn):
        deps.repos.runs.set_status(run_id, "failed", deps.now())
