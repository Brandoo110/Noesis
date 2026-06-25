import json
from sqlite3 import Connection

from noesis.db.connection import with_tx
from noesis.db.models import (
    EvidenceRow,
    IntelItemRow,
    ThesisAssumptionRow,
    ThesisRow,
)
from noesis.graph.errors import ResearchNodeError
from noesis.graph.schemas import (
    ConfirmationResult,
    DegradeNote,
    EvidenceRecord,
    IntelItemDraft,
    ThesisAssumptionDraft,
    ThesisDraft,
)
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate

REQUIRED_STATE_KEYS = ("run_id", "position_id", "entity_id")
OUTPUT_STATE_KEYS = ("evidence_ids", "intel_item_ids", "thesis_id", "degraded")


def finalize(state: ResearchState, deps: GraphDeps) -> ResearchStateUpdate:
    run_id = state.get("run_id")
    position_id = state.get("position_id")
    entity_id = state.get("entity_id")
    if run_id is None or position_id is None or entity_id is None:
        raise ResearchNodeError("run_id, position_id and entity_id are required", reason="missing_ids")
    conn: Connection = deps.repos.conn
    now = deps.now()
    confirmation = state.get("confirmation") or ConfirmationResult(status="confirmed")
    thesis_draft = state.get("thesis_draft")
    degraded = list(state.get("degraded", []))
    if thesis_draft is None:
        degraded.append(
            DegradeNote(
                node_name="finalize",
                reason="thesis_draft_missing",
                fallback_used="complete_without_thesis",
            )
        )
    with with_tx(conn):
        _persist_evidences(state.get("evidences", []), entity_id, now, deps, conn)
        intel_ids = _persist_intel(state.get("intel_items", []), run_id, entity_id, now, deps, conn)
        thesis_id = _persist_thesis(
            thesis_draft,
            confirmation,
            position_id,
            run_id,
            now,
            deps,
            conn,
        )
        _finalize_approval(thesis_id, confirmation.status, now, deps, conn)
        deps.repos.runs.set_status(run_id, "completed", now, conn=conn)
    return {
        "evidence_ids": [item.id for item in state.get("evidences", [])],
        "intel_item_ids": intel_ids,
        "thesis_id": thesis_id,
        "degraded": degraded,
    }


def _persist_evidences(
    evidences: list[EvidenceRecord],
    entity_id: str,
    now: str,
    deps: GraphDeps,
    conn: Connection,
) -> None:
    rows = [
        EvidenceRow(
            id=item.id,
            run_id=item.run_id,
            entity_id=entity_id,
            source=item.source,
            source_tier=item.source_tier,
            url=item.url,
            title=item.title,
            snippet=item.snippet,
            captured_at=item.captured_at,
            published_at=item.published_at,
            created_at=now,
        )
        for item in evidences
        if deps.repos.evidences.get(item.id, conn=conn) is None
    ]
    if rows:
        deps.repos.evidences.insert_many(rows, conn=conn)


def _persist_intel(
    items: list[IntelItemDraft],
    run_id: str,
    entity_id: str,
    now: str,
    deps: GraphDeps,
    conn: Connection,
) -> list[str]:
    rows: list[IntelItemRow] = []
    for index, item in enumerate(items, start=1):
        row_id = f"intel-{run_id}-{index}"
        rows.append(
            IntelItemRow(
                id=row_id,
                entity_id=entity_id,
                run_id=run_id,
                source=item.source,
                source_tier=item.source_tier,
                title=item.title,
                content=item.content,
                url=item.url,
                published_at=item.published_at,
                sentiment_json=item.sentiment.model_dump_json(),
                event_type=item.event_type,
                evidence_ids_json=json.dumps(item.evidence_ids, sort_keys=True),
                created_at=now,
            )
        )
    if rows:
        deps.repos.intel.insert_many(rows, conn=conn)
    return [row.id for row in rows]


def _persist_thesis(
    draft: ThesisDraft | None,
    confirmation: ConfirmationResult,
    position_id: str,
    run_id: str,
    now: str,
    deps: GraphDeps,
    conn: Connection,
) -> str | None:
    if draft is None:
        return None
    thesis_id = f"thesis-{run_id}"
    summary = confirmation.edited_summary if confirmation.status == "edited" else None
    assumptions = confirmation.edited_assumptions if confirmation.status == "edited" else None
    deps.repos.theses.insert(
        ThesisRow(
            id=thesis_id,
            position_id=position_id,
            run_id=run_id,
            summary=summary or draft.summary,
            status=confirmation.status,
            created_at=now,
            updated_at=now,
        ),
        conn=conn,
    )
    _persist_assumptions(thesis_id, assumptions or draft.assumptions, confirmation.status, now, deps, conn)
    return thesis_id


def _persist_assumptions(
    thesis_id: str,
    assumptions: list[ThesisAssumptionDraft],
    status: str,
    now: str,
    deps: GraphDeps,
    conn: Connection,
) -> None:
    rows = [
        ThesisAssumptionRow(
            id=f"assumption-{thesis_id}-{index}",
            thesis_id=thesis_id,
            text=item.text,
            kind=item.kind,
            evidence_ids_json=json.dumps(item.evidence_ids, sort_keys=True),
            status=status,
            created_at=now,
        )
        for index, item in enumerate(assumptions, start=1)
    ]
    if rows:
        deps.repos.assumptions.insert_many(rows, conn=conn)


def _finalize_approval(
    thesis_id: str | None,
    status: str,
    now: str,
    deps: GraphDeps,
    conn: Connection,
) -> None:
    if thesis_id is None:
        return
    approval = deps.repos.approvals.get_by_object("thesis", thesis_id, conn=conn)
    if approval is not None:
        deps.repos.approvals.set_status(approval.id, status, now, conn=conn)
