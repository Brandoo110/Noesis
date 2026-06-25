from collections.abc import Mapping

from langgraph.types import interrupt

from noesis.db.models import ApprovalRow
from noesis.graph.errors import ResearchNodeError
from noesis.graph.schemas import ConfirmationResult, DegradeNote
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate

REQUIRED_STATE_KEYS = ("run_id", "thesis_draft")
OUTPUT_STATE_KEYS = ("confirmation", "degraded")


def human_confirm(state: ResearchState, deps: GraphDeps) -> ResearchStateUpdate:
    run_id = state.get("run_id")
    if run_id is None:
        raise ResearchNodeError("run_id is required", reason="missing_run_id")
    degraded = list(state.get("degraded", []))
    thesis_draft = state.get("thesis_draft")
    if thesis_draft is None:
        degraded.append(
            DegradeNote(
                node_name="human_confirm",
                reason="thesis_draft_missing",
                fallback_used="skip_confirmation",
            )
        )
        return {"confirmation": ConfirmationResult(status="confirmed"), "degraded": degraded}
    approval = _get_or_create_approval(run_id, thesis_draft.model_dump_json(), deps)
    deps.repos.runs.set_status(run_id, "awaiting_confirmation", None)
    resume_value: object = interrupt(
        {
            "approval_id": approval.id,
            "object_type": approval.object_type,
            "object_id": approval.object_id,
            "run_id": run_id,
        }
    )
    return {"confirmation": _confirmation_from_resume(resume_value), "degraded": degraded}


def _get_or_create_approval(run_id: str, payload_json: str, deps: GraphDeps) -> ApprovalRow:
    object_id = f"thesis-{run_id}"
    existing = deps.repos.approvals.get_by_object("thesis", object_id)
    if existing is not None:
        return existing
    approval = _make_approval(run_id, payload_json, deps.now())
    deps.repos.approvals.insert(approval)
    return approval


def _make_approval(run_id: str, payload_json: str, now: str) -> ApprovalRow:
    return ApprovalRow(
        id=f"approval-{run_id}",
        run_id=run_id,
        object_type="thesis",
        object_id=f"thesis-{run_id}",
        status="pending",
        payload_json=payload_json,
        created_at=now,
        updated_at=now,
    )


def _confirmation_from_resume(value: object) -> ConfirmationResult:
    if isinstance(value, Mapping):
        return ConfirmationResult.model_validate(value)
    return ConfirmationResult(status="confirmed")
