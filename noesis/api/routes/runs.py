from fastapi import APIRouter, Depends

from noesis.api.deps import get_graph_deps
from noesis.api.dto import (
    CreateRunRequest,
    EvidenceResponse,
    IntelItemResponse,
    RunDetailResponse,
    RunResponse,
    SentimentResponse,
    ThesisAssumptionResponse,
    ThesisResponse,
)
from noesis.graph.runner import RunHandle, RunSnapshot, get_run_snapshot, start_run
from noesis.graph.schemas import EvidenceRecord, IntelItemDraft, ThesisDraft
from noesis.graph.state import GraphDeps

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunResponse)
def create_run(
    request: CreateRunRequest,
    deps: GraphDeps = Depends(get_graph_deps),
) -> RunResponse:
    return _run_response(start_run(request.position_id, deps))


@router.get("/{run_id}", response_model=RunDetailResponse)
def get_run(
    run_id: str,
    deps: GraphDeps = Depends(get_graph_deps),
) -> RunDetailResponse:
    return _detail_response(get_run_snapshot(run_id, deps))


def _run_response(handle: RunHandle) -> RunResponse:
    return RunResponse(
        run_id=handle.run_id,
        status=handle.status,
        thesis_id=handle.thesis_id,
    )


def _detail_response(snapshot: RunSnapshot) -> RunDetailResponse:
    return RunDetailResponse(
        run_id=snapshot.run_id,
        status=snapshot.status,
        thesis_id=snapshot.thesis_id,
        evidences=[_evidence_response(item) for item in snapshot.evidences],
        intel_items=[_intel_response(item) for item in snapshot.intel_items],
        thesis=_thesis_response(snapshot),
    )


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
