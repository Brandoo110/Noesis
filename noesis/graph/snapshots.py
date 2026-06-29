from collections.abc import Mapping
from typing import TYPE_CHECKING

from noesis.db.models import EvidenceRow, IntelItemRow, ThesisRow
from noesis.graph.build_graph import build_seed_graph
from noesis.graph.errors import ResearchNodeError
from noesis.graph.schemas import (
    EvidenceRecord,
    IntelItemDraft,
    ResolvedEntity,
    ThesisAssumptionDraft,
    ThesisDraft,
)
from noesis.graph.state import GraphDeps
from noesis.graph.tracing import trace_node

if TYPE_CHECKING:
    from noesis.graph.runner import RunSnapshot


def get_run_snapshot(run_id: str, deps: GraphDeps) -> "RunSnapshot":
    from noesis.graph.runner import RunSnapshot

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


def _typed_list(value: object, item_type: type) -> list:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, item_type)]


def _checkpoint_values(run_id: str, deps: GraphDeps) -> Mapping[str, object]:
    if deps.checkpointer is None:
        raise ResearchNodeError("checkpointer is required", reason="missing_checkpointer")
    graph = build_seed_graph(deps, checkpointer=deps.checkpointer, node_wrapper=trace_node)
    snapshot = graph.get_state({"configurable": {"thread_id": run_id}})
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
