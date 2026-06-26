import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from uuid import uuid4

from langgraph.types import Command

from noesis.db.connection import with_tx
from noesis.db.models import EntityRow, RunRow
from noesis.db.models import EvidenceRow, IntelItemRow, ThesisRow
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
    ThesisAssumptionDraft,
    ThesisDraft,
)
from noesis.graph.state import GraphDeps, ResearchState
from noesis.graph.tracing import trace_node
from noesis.tools.llm.router import LLMRouter
from noesis.tools.retrieval.store import EvidenceRetriever
from noesis.tools.search.base import SearchAdapter


@dataclass(frozen=True)
class RunHandle:
    run_id: str
    status: str
    thesis_id: str | None = None


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
    return _handle(run_id, deps)


def get_run_snapshot(run_id: str, deps: GraphDeps) -> RunSnapshot:
    row = deps.repos.runs.get(run_id)
    if row is None:
        raise ResearchNodeError("run not found", reason="run_not_found")
    values = _checkpoint_values(run_id, deps)
    resolved_entity = values.get("resolved_entity")
    if not isinstance(resolved_entity, ResolvedEntity):
        resolved_entity = None
    evidences = _typed_list(values.get("evidences"), EvidenceRecord)
    intel_items = _typed_list(values.get("intel_items"), IntelItemDraft)
    thesis_draft = values.get("thesis_draft")
    if not isinstance(thesis_draft, ThesisDraft):
        thesis_draft = None
    evidence_rows = deps.repos.evidences.list_by_run(run_id)
    if not evidences:
        evidences = [_evidence_from_row(item) for item in evidence_rows]
    if not intel_items:
        intel_items = _intel_from_rows(run_id, evidence_rows, deps)
    thesis_id = f"thesis-{run_id}"
    thesis_row = deps.repos.theses.get(thesis_id)
    thesis_status = "draft" if thesis_draft is not None else None
    if thesis_row is not None:
        thesis_draft = _thesis_from_row(thesis_row, deps)
        thesis_status = thesis_row.status
    return RunSnapshot(
        run_id=run_id,
        status=row.status,
        thesis_id=thesis_id if thesis_draft is not None else None,
        thesis_status=thesis_status,
        resolved_entity=resolved_entity,
        evidences=evidences,
        intel_items=intel_items,
        thesis_draft=thesis_draft,
    )


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
    symbol = identifiers.get("symbol") or entity.name
    return PositionInput(
        symbol=symbol,
        market=entity.market or "",
        name=entity.name,
        kind="watching",
    )


def _typed_list(value: object, item_type: type) -> list:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, item_type)]


def _checkpoint_values(run_id: str, deps: GraphDeps) -> Mapping[str, object]:
    graph = _graph(deps)
    snapshot = graph.get_state(_config(run_id))
    values = getattr(snapshot, "values", {})
    return values if isinstance(values, Mapping) else {}


def _evidence_from_row(row: EvidenceRow) -> EvidenceRecord:
    return EvidenceRecord(
        id=row.id,
        run_id=row.run_id,
        source=row.source,
        source_tier=row.source_tier,
        url=row.url,
        title=row.title,
        snippet=row.snippet,
        captured_at=row.captured_at,
        published_at=row.published_at,
    )


def _intel_from_rows(
    run_id: str, evidence_rows: list[EvidenceRow], deps: GraphDeps
) -> list[IntelItemDraft]:
    entity_id = next((row.entity_id for row in evidence_rows if row.entity_id), None)
    if entity_id is None:
        return []
    rows = deps.repos.intel.list_by_entity(entity_id)
    return [_intel_from_row(row) for row in rows if row.run_id == run_id]


def _intel_from_row(row: IntelItemRow) -> IntelItemDraft:
    return IntelItemDraft(
        title=row.title,
        content=row.content,
        event_type=row.event_type,
        source=row.source,
        source_tier=row.source_tier,
        url=row.url,
        published_at=row.published_at,
        sentiment=row.sentiment(),
        evidence_ids=row.evidence_ids(),
    )


def _thesis_from_row(row: ThesisRow, deps: GraphDeps) -> ThesisDraft:
    assumptions = [
        ThesisAssumptionDraft(
            text=item.text,
            kind=item.kind,
            evidence_ids=item.evidence_ids(),
        )
        for item in deps.repos.assumptions.list_by_thesis(row.id)
    ]
    return ThesisDraft(summary=row.summary, assumptions=assumptions)


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
