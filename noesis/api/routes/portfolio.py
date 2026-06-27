from fastapi import APIRouter, Depends

from noesis.api.deps import get_graph_deps
from noesis.api.dto import OverlapGroupResponse, OverlapPositionResponse
from noesis.graph.state import GraphDeps
from noesis.graph.traversal import OverlapGroup, portfolio_overlap

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/overlaps", response_model=list[OverlapGroupResponse])
def get_portfolio_overlaps(
    deps: GraphDeps = Depends(get_graph_deps),
) -> list[OverlapGroupResponse]:
    positions = deps.repos.positions.list_by_user("local-user")
    positions_with_seed: list[tuple[str, str, str]] = []
    for position in positions:
        seed_entity_id = deps.repos.runs.get_seed_entity_id(position.id)
        if seed_entity_id is None:
            continue
        positions_with_seed.append((position.id, position.symbol, seed_entity_id))
    groups = portfolio_overlap(
        positions_with_seed,
        deps.repos.graph_edges,
        deps.repos.entities,
    )
    return [_overlap_response(group) for group in groups]


def _overlap_response(group: OverlapGroup) -> OverlapGroupResponse:
    return OverlapGroupResponse(
        segment_id=group.segment_id,
        segment_name=group.segment_name,
        node_type=group.node_type,
        basis=group.basis,
        positions=[
            OverlapPositionResponse(
                position_id=position.position_id,
                symbol=position.symbol,
                entity_id=position.entity_id,
                confidence=position.confidence,
            )
            for position in group.positions
        ],
    )
