from fastapi import APIRouter, Depends, HTTPException

from noesis.api.deps import get_graph_deps
from noesis.api.dto import EvidenceResponse
from noesis.db.models import EvidenceRow
from noesis.graph.state import GraphDeps

router = APIRouter(prefix="/evidences", tags=["evidences"])


@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(
    evidence_id: str,
    deps: GraphDeps = Depends(get_graph_deps),
) -> EvidenceResponse:
    row = deps.repos.evidences.get(evidence_id)
    if row is None:
        raise HTTPException(status_code=404, detail="evidence not found")
    return _evidence_response(row)


def _evidence_response(row: EvidenceRow) -> EvidenceResponse:
    return EvidenceResponse(
        id=row.id,
        source=row.source,
        source_tier=row.source_tier,
        url=row.url,
        title=row.title,
        snippet=row.snippet,
        captured_at=row.captured_at,
        published_at=row.published_at,
    )
