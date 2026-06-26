from fastapi import APIRouter, Depends

from noesis.api.deps import get_graph_deps
from noesis.api.dto import (
    EdgeResponse,
    EntityNodeResponse,
    ExpandRequest,
    ExpandResponse,
)
from noesis.db.models import EntityRow, GraphEdgeRow
from noesis.graph.errors import ResearchNodeError
from noesis.graph.runner import start_expand_run
from noesis.graph.state import GraphDeps

router = APIRouter(prefix="/entities", tags=["entities"])


@router.post("/{entity_id}/expand", response_model=ExpandResponse)
def expand_entity(
    entity_id: str,
    request: ExpandRequest,
    deps: GraphDeps = Depends(get_graph_deps),
) -> ExpandResponse:
    handle = start_expand_run(entity_id, request.position_id, deps)
    edges = deps.repos.graph_edges.list_from(entity_id)
    return ExpandResponse(
        entity_id=entity_id,
        run_id=handle.run_id,
        status=handle.status,
        edges=[_edge_response(edge, deps) for edge in edges],
    )


def _edge_response(edge: GraphEdgeRow, deps: GraphDeps) -> EdgeResponse:
    neighbor = deps.repos.entities.get(edge.to_entity_id)
    if neighbor is None:
        raise ResearchNodeError("edge neighbor not found", reason="entity_not_found")
    evidence_ids = edge.evidence_ids()
    return EdgeResponse(
        id=edge.id,
        to_entity_id=edge.to_entity_id,
        to_name=neighbor.name,
        to_symbol=neighbor.identifiers().get("symbol"),
        relation=edge.relation,
        basis=edge.basis,
        confidence=edge.confidence,
        evidence_ids=evidence_ids,
        source_tier=_source_tier(evidence_ids, deps),
        rationale=edge.rationale,
        neighbor=_entity_response(neighbor),
    )


def _entity_response(row: EntityRow) -> EntityNodeResponse:
    return EntityNodeResponse(
        id=row.id,
        name=row.name,
        node_type=row.node_type,
        symbol=row.identifiers().get("symbol"),
        market=row.market,
    )


def _source_tier(evidence_ids: list[str], deps: GraphDeps) -> int | None:
    tiers = [
        row.source_tier
        for evidence_id in evidence_ids
        if (row := deps.repos.evidences.get(evidence_id)) is not None
    ]
    return min(tiers) if tiers else None
