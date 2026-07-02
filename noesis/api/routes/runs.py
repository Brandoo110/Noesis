from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends

from noesis.api.deps import get_graph_deps
from noesis.api.dto import (
    CreateRunRequest,
    EntityNodeResponse,
    EvidenceResponse,
    IntelItemResponse,
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
        SELECT
          r.id, r.status, r.started_at, r.ended_at,
          COUNT(DISTINCT e.id) AS evidence_count,
          COUNT(t.id) AS tool_count,
          COALESCE(SUM(CASE WHEN t.cache_hit = 1 THEN 1 ELSE 0 END), 0)
            AS cache_hits
        FROM run_registry r
        LEFT JOIN evidences e ON e.run_id = r.id
        LEFT JOIN tool_invocations t ON t.run_id = r.id
        GROUP BY r.id
        ORDER BY r.started_at DESC, r.created_at DESC, r.id DESC
        """
    ).fetchall()
    return RunListResponse(
        runs=[
            RunSummaryResponse(
                run_id=str(row["id"]),
                status=str(row["status"]),
                started_at=str(row["started_at"]),
                ended_at=row["ended_at"],
                latency_ms=_latency_ms(row["started_at"], row["ended_at"]),
                evidence_count=int(row["evidence_count"]),
                tool_count=int(row["tool_count"]),
                cache_hit_rate=_ratio(int(row["cache_hits"]), int(row["tool_count"])),
            )
            for row in rows
        ]
    )


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
            )
            for tool in deps.repos.tool_invocations.list_by_run(run_id)
        ],
    ]
    steps.sort(key=lambda item: (item.started_at, item.kind != "node", item.name))
    return RunTraceResponse(run_id=run.id, status=run.status, steps=steps)


def _run_response(handle: RunHandle) -> RunResponse:
    return RunResponse(
        run_id=handle.run_id,
        status=handle.status,
        thesis_id=handle.thesis_id,
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
