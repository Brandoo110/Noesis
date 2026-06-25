import json
from collections.abc import Callable, Mapping
from uuid import uuid4

from langgraph.errors import GraphBubbleUp

from noesis.db.connection import with_tx
from noesis.db.models import NodeTraceRow
from noesis.graph.errors import ResearchNodeError
from noesis.graph.schemas import EvidenceRecord, IntelItemDraft, ThesisDraft
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate

NodeFn = Callable[[ResearchState, GraphDeps], ResearchStateUpdate]


def trace_node(
    node_name: str, node_fn: NodeFn, deps: GraphDeps
) -> Callable[[ResearchState], ResearchStateUpdate]:
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
