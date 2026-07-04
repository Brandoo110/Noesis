from datetime import UTC, datetime
from collections import defaultdict

from fastapi import APIRouter, BackgroundTasks, Depends

from noesis.agentops.diagnostics import (
    DiagnosticStep,
    RunDiagnostic,
    build_run_diagnostic,
)
from noesis.db.connection import with_tx
from noesis.db.models import EvidenceRow, NodeTraceRow, ToolInvocationRow
from noesis.api.deps import get_graph_deps
from noesis.api.dto import (
    ClearRunsResponse,
    CreateRunRequest,
    EntityNodeResponse,
    EvidenceResponse,
    EvidencePreviewResponse,
    IntelItemResponse,
    RunDiagnosticResponse,
    RunDetailResponse,
    RunListResponse,
    RunResponse,
    RunSummaryResponse,
    RunTraceResponse,
    RunTraceStepResponse,
    SentimentResponse,
    ThesisAssumptionResponse,
    ThesisResponse,
)
from noesis.api.routes.entities import _entity_response
from noesis.graph.runner import (
    RunHandle,
    RunSnapshot,
    create_seed_run,
    execute_seed_run,
    get_run_snapshot,
)
from noesis.graph.errors import ResearchNodeError
from noesis.graph.schemas import EvidenceRecord, IntelItemDraft, ThesisDraft
from noesis.graph.state import GraphDeps

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=RunListResponse)
def list_runs(deps: GraphDeps = Depends(get_graph_deps)) -> RunListResponse:
    rows = deps.repos.conn.execute(
        """
        WITH evidence_counts AS (
          SELECT run_id, COUNT(*) AS evidence_count
          FROM evidences
          GROUP BY run_id
        ),
        tool_counts AS (
          SELECT
            run_id,
            COUNT(*) AS tool_count,
            SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) AS cache_hits
          FROM tool_invocations
          GROUP BY run_id
        )
        SELECT
          r.id, r.status, r.started_at, r.ended_at,
          COALESCE(e.evidence_count, 0) AS evidence_count,
          COALESCE(t.tool_count, 0) AS tool_count,
          COALESCE(t.cache_hits, 0) AS cache_hits
        FROM run_registry r
        LEFT JOIN evidence_counts e ON e.run_id = r.id
        LEFT JOIN tool_counts t ON t.run_id = r.id
        ORDER BY r.started_at DESC, r.created_at DESC, r.id DESC
        """
    ).fetchall()
    run_ids = [str(row["id"]) for row in rows]
    steps_by_run = _diagnostic_steps_by_run(deps, run_ids)
    return RunListResponse(
        runs=[
            _run_summary_response(row, steps_by_run[str(row["id"])])
            for row in rows
        ]
    )


@router.delete("", response_model=ClearRunsResponse)
def clear_runs(deps: GraphDeps = Depends(get_graph_deps)) -> ClearRunsResponse:
    tables = (
        "node_traces",
        "tool_invocations",
        "tool_cache_entries",
        "source_documents",
        "evidences_fts",
        "evidences",
        "intel_items",
        "thesis_assumptions",
        "theses",
        "approvals",
        "graph_edges",
        "node_expansions",
        "holding_relevances",
        "run_registry",
    )
    deleted = {table: _table_count(deps, table) for table in tables}
    with with_tx(deps.repos.conn):
        for table in tables:
            deps.repos.conn.execute(f"DELETE FROM {table}")
    return ClearRunsResponse(deleted=deleted)


@router.post("", response_model=RunResponse)
def create_run(
    request: CreateRunRequest,
    background_tasks: BackgroundTasks,
    deps: GraphDeps = Depends(get_graph_deps),
) -> RunResponse:
    handle = create_seed_run(request.position_id, deps)
    if handle.created:
        background_tasks.add_task(execute_seed_run, handle.run_id, deps)
    return _run_response(handle)


@router.get("/{run_id}", response_model=RunDetailResponse)
def get_run(
    run_id: str,
    deps: GraphDeps = Depends(get_graph_deps),
) -> RunDetailResponse:
    return _detail_response(get_run_snapshot(run_id, deps), deps)


@router.get("/{run_id}/trace", response_model=RunTraceResponse)
def get_run_trace(
    run_id: str,
    deps: GraphDeps = Depends(get_graph_deps),
) -> RunTraceResponse:
    run = deps.repos.runs.get(run_id)
    if run is None:
        raise ResearchNodeError("run not found", reason="run_not_found")
    steps = [
        *[
            RunTraceStepResponse(
                kind="node",
                name=trace.node_name,
                status=trace.status,
                started_at=trace.started_at,
                ended_at=trace.ended_at,
                latency_ms=_latency_ms(trace.started_at, trace.ended_at),
                input_summary=trace.inputs_ref,
                output_summary=trace.outputs_ref,
                cache_hit=None,
                retry_count=None,
                evidence_ids=trace.evidence_ids(),
                model_id=trace.model_id,
                fallback_used=trace.fallback_used,
                degraded_reason=trace.reason,
            )
            for trace in deps.repos.traces.list_by_run(run_id)
        ],
        *[
            RunTraceStepResponse(
                kind="tool",
                name=tool.tool_name,
                status=tool.status,
                started_at=tool.started_at,
                ended_at=tool.ended_at,
                latency_ms=tool.latency_ms,
                input_summary=tool.input_summary,
                output_summary=tool.output_summary,
                cache_hit=tool.cache_hit,
                retry_count=tool.retry_count,
                evidence_ids=[],
                error_kind=_error_kind(tool.error_message),
                error_code="tool_failed" if tool.status == "failed" else None,
                error_message=tool.error_message,
                http_status=None,
                provider=_provider_name(tool.tool_name),
                model_id=None,
                token_input=tool.token_input,
                token_output=tool.token_output,
                estimated_cost_usd=tool.estimated_cost_usd,
                cache_key=tool.cache_key,
            )
            for tool in deps.repos.tool_invocations.list_by_run(run_id)
        ],
    ]
    steps.sort(key=lambda item: (item.started_at, item.kind != "node", item.name))
    evidence_previews = _evidence_previews(deps, steps)
    diagnostic = build_run_diagnostic(
        status=run.status,
        evidence_count=len(evidence_previews),
        tool_count=sum(1 for step in steps if step.kind == "tool"),
        steps=[_diagnostic_step_from_response(step) for step in steps],
    )
    return RunTraceResponse(
        run_id=run.id,
        status=run.status,
        diagnostic=_diagnostic_response(diagnostic),
        steps=steps,
        evidence_previews=evidence_previews,
    )


def _run_response(handle: RunHandle) -> RunResponse:
    return RunResponse(
        run_id=handle.run_id,
        status=handle.status,
        thesis_id=handle.thesis_id,
    )


def _run_summary_response(row, steps: list[DiagnosticStep]) -> RunSummaryResponse:
    status = str(row["status"])
    evidence_count = int(row["evidence_count"])
    tool_count = int(row["tool_count"])
    diagnostic = build_run_diagnostic(
        status=status,
        evidence_count=evidence_count,
        tool_count=tool_count,
        steps=steps,
    )
    return RunSummaryResponse(
        run_id=str(row["id"]),
        status=status,
        started_at=str(row["started_at"]),
        ended_at=row["ended_at"],
        latency_ms=_latency_ms(row["started_at"], row["ended_at"]),
        evidence_count=evidence_count,
        tool_count=tool_count,
        cache_hit_rate=_ratio(int(row["cache_hits"]), tool_count),
        diagnostic_tags=diagnostic.tags,
        last_step_name=diagnostic.last_step_name,
        slowest_step_name=diagnostic.slowest_step_name,
        slowest_step_latency_ms=diagnostic.slowest_step_latency_ms,
        has_degraded_step=diagnostic.has_degraded_step,
        has_failed_step=diagnostic.has_failed_step,
        has_pending_confirmation=diagnostic.has_pending_confirmation,
    )


def _detail_response(snapshot: RunSnapshot, deps: GraphDeps) -> RunDetailResponse:
    return RunDetailResponse(
        run_id=snapshot.run_id,
        status=snapshot.status,
        thesis_id=snapshot.thesis_id,
        entity=_resolved_entity_response(snapshot, deps),
        evidences=[_evidence_response(item) for item in snapshot.evidences],
        intel_items=[_intel_response(item) for item in snapshot.intel_items],
        thesis=_thesis_response(snapshot),
    )


def _resolved_entity_response(
    snapshot: RunSnapshot, deps: GraphDeps
) -> EntityNodeResponse | None:
    if snapshot.resolved_entity is None:
        return None
    row = deps.repos.entities.get(snapshot.resolved_entity.entity_id)
    return _entity_response(row) if row is not None else None


def _evidence_response(item: EvidenceRecord) -> EvidenceResponse:
    return EvidenceResponse(
        id=item.id,
        source=item.source,
        source_tier=item.source_tier,
        url=item.url,
        title=item.title,
        snippet=item.snippet,
        captured_at=item.captured_at,
        published_at=item.published_at,
    )


def _evidence_preview_response(item: EvidenceRow) -> EvidencePreviewResponse:
    return EvidencePreviewResponse(
        evidence_id=item.id,
        title=item.title,
        source=item.source,
        url=item.url,
        snippet=item.snippet,
        source_tier=item.source_tier,
        published_at=item.published_at,
    )


def _evidence_previews(
    deps: GraphDeps, steps: list[RunTraceStepResponse]
) -> list[EvidencePreviewResponse]:
    evidence_ids = [
        evidence_id
        for step in steps
        for evidence_id in step.evidence_ids
    ]
    rows = deps.repos.evidences.list_by_ids(evidence_ids, conn=deps.repos.conn)
    return [_evidence_preview_response(row) for row in rows]


def _intel_response(item: IntelItemDraft) -> IntelItemResponse:
    return IntelItemResponse(
        title=item.title,
        content=item.content,
        event_type=item.event_type,
        source=item.source,
        source_tier=item.source_tier,
        url=item.url,
        published_at=item.published_at,
        sentiment=SentimentResponse(
            dir=item.sentiment.dir,
            conf=item.sentiment.conf,
        ),
        evidence_ids=item.evidence_ids,
    )


def _thesis_response(snapshot: RunSnapshot) -> ThesisResponse | None:
    draft = snapshot.thesis_draft
    if draft is None or snapshot.thesis_id is None or snapshot.thesis_status is None:
        return None
    return _draft_response(snapshot.thesis_id, snapshot.thesis_status, draft)


def _draft_response(
    thesis_id: str, thesis_status: str, draft: ThesisDraft
) -> ThesisResponse:
    return ThesisResponse(
        id=thesis_id,
        summary=draft.summary,
        status=thesis_status,
        assumptions=[
            ThesisAssumptionResponse(
                text=item.text,
                kind=item.kind,
                evidence_ids=item.evidence_ids,
            )
            for item in draft.assumptions
        ],
    )


def _latency_ms(started_at: str, ended_at: str | None) -> int | None:
    if ended_at is None:
        return None
    started = _parse_iso(started_at)
    ended = _parse_iso(ended_at)
    return max(0, int((ended - started).total_seconds() * 1000))


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0
    return round(numerator / denominator, 4)


def _table_count(deps: GraphDeps, table: str) -> int:
    row = deps.repos.conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    return int(row["count"]) if row is not None else 0


def _diagnostic_response(diagnostic: RunDiagnostic) -> RunDiagnosticResponse:
    return RunDiagnosticResponse(
        severity=diagnostic.severity,
        title=diagnostic.title,
        summary=diagnostic.summary,
        tags=diagnostic.tags,
        slowest_step_name=diagnostic.slowest_step_name,
        slowest_step_latency_ms=diagnostic.slowest_step_latency_ms,
        next_actions=diagnostic.next_actions,
    )


def _diagnostic_steps_by_run(
    deps: GraphDeps, run_ids: list[str]
) -> dict[str, list[DiagnosticStep]]:
    grouped: dict[str, list[DiagnosticStep]] = defaultdict(list)
    for trace in deps.repos.traces.list_by_run_ids(run_ids):
        grouped[trace.run_id].append(_diagnostic_step_from_trace(trace))
    for tool in deps.repos.tool_invocations.list_by_run_ids(run_ids):
        grouped[tool.run_id].append(_diagnostic_step_from_tool(tool))
    return grouped


def _diagnostic_step_from_response(
    step: RunTraceStepResponse,
) -> DiagnosticStep:
    return DiagnosticStep(
        name=step.name,
        kind=step.kind,
        status=step.status,
        started_at=step.started_at,
        ended_at=step.ended_at,
        latency_ms=step.latency_ms,
        retry_count=step.retry_count,
        evidence_ids=step.evidence_ids,
    )


def _diagnostic_step_from_trace(trace: NodeTraceRow) -> DiagnosticStep:
    return DiagnosticStep(
        name=trace.node_name,
        kind="node",
        status=trace.status,
        started_at=trace.started_at,
        ended_at=trace.ended_at,
        latency_ms=_latency_ms(trace.started_at, trace.ended_at),
        retry_count=None,
        evidence_ids=trace.evidence_ids(),
    )


def _diagnostic_step_from_tool(tool: ToolInvocationRow) -> DiagnosticStep:
    return DiagnosticStep(
        name=tool.tool_name,
        kind="tool",
        status=tool.status,
        started_at=tool.started_at,
        ended_at=tool.ended_at,
        latency_ms=tool.latency_ms,
        retry_count=tool.retry_count,
        evidence_ids=[],
    )


def _error_kind(message: str | None) -> str | None:
    if not message:
        return None
    lowered = message.lower()
    if "timeout" in lowered:
        return "timeout"
    if "rate limit" in lowered or "429" in lowered:
        return "rate_limit"
    if "auth" in lowered or "401" in lowered or "403" in lowered:
        return "auth"
    if "network" in lowered or "connection" in lowered:
        return "network"
    if "schema" in lowered or "json" in lowered:
        return "schema_parse"
    if "provider" in lowered or "5" in lowered:
        return "provider_error"
    return "unknown"


def _provider_name(tool_name: str) -> str | None:
    if "." not in tool_name:
        return None
    return tool_name.split(".", 1)[0]
