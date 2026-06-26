from fastapi import APIRouter, Depends

from noesis.api.deps import get_graph_deps
from noesis.api.dto import (
    EdgeResponse,
    EntityNodeResponse,
    ExpandRequest,
    ExpandResponse,
    NeighborsResponse,
    RelevanceResponse,
)
from noesis.db.models import EntityRow, GraphEdgeRow
from noesis.graph.errors import ResearchNodeError
from noesis.graph.runner import start_expand_run
from noesis.graph.state import GraphDeps
from noesis.graph.traversal import relevance_path

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


@router.get("/{entity_id}/neighbors", response_model=NeighborsResponse)
def list_neighbors(
    entity_id: str,
    deps: GraphDeps = Depends(get_graph_deps),
) -> NeighborsResponse:
    edges = deps.repos.graph_edges.list_from(entity_id)
    return NeighborsResponse(
        entity_id=entity_id,
        edges=[_edge_response(edge, deps) for edge in edges],
    )


@router.get("/{entity_id}/relevance", response_model=RelevanceResponse)
def get_relevance(
    entity_id: str,
    position_id: str,
    deps: GraphDeps = Depends(get_graph_deps),
) -> RelevanceResponse:
    seed_entity_id = deps.repos.runs.get_seed_entity_id(position_id)
    path_ids = (
        relevance_path(entity_id, seed_entity_id, deps.repos.graph_edges)
        if seed_entity_id is not None
        else None
    )
    return RelevanceResponse(
        entity_id=entity_id,
        position_id=position_id,
        path=_entity_path(path_ids or [], deps),
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


def _entity_path(entity_ids: list[str], deps: GraphDeps) -> list[EntityNodeResponse]:
    rows: list[EntityNodeResponse] = []
    for entity_id in entity_ids:
        row = deps.repos.entities.get(entity_id)
        if row is None:
            raise ResearchNodeError("path entity not found", reason="entity_not_found")
        rows.append(_entity_response(row))
    return rows


def _source_tier(evidence_ids: list[str], deps: GraphDeps) -> int | None:
    tiers = [
        row.source_tier
        for evidence_id in evidence_ids
        if (row := deps.repos.evidences.get(evidence_id)) is not None
    ]
    return min(tiers) if tiers else None
