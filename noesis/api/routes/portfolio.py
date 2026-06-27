from fastapi import APIRouter, Depends

from noesis.api.deps import get_graph_deps
from noesis.api.dto import (
    BriefPositionResponse,
    OverlapGroupResponse,
    OverlapPositionResponse,
    PortfolioBriefResponse,
)
from noesis.db.models import PositionRow
from noesis.graph.state import GraphDeps
from noesis.graph.traversal import OverlapGroup, portfolio_overlap

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/overlaps", response_model=list[OverlapGroupResponse])
def get_portfolio_overlaps(
    deps: GraphDeps = Depends(get_graph_deps),
) -> list[OverlapGroupResponse]:
    positions = deps.repos.positions.list_by_user("local-user")
    return [
        _overlap_response(group)
        for group in _portfolio_overlap_groups(deps, positions)
    ]


@router.get("/brief", response_model=PortfolioBriefResponse)
def get_portfolio_brief(
    deps: GraphDeps = Depends(get_graph_deps),
) -> PortfolioBriefResponse:
    positions = deps.repos.positions.list_by_user("local-user")
    return PortfolioBriefResponse(
        generated_at=deps.now(),
        positions=[_brief_position_response(position, deps) for position in positions],
        overlaps=[
            _overlap_response(group)
            for group in _portfolio_overlap_groups(deps, positions)
        ],
    )


def _portfolio_overlap_groups(
    deps: GraphDeps, positions: list[PositionRow]
) -> list[OverlapGroup]:
    return portfolio_overlap(
        _positions_with_seed(deps, positions),
        deps.repos.graph_edges,
        deps.repos.entities,
    )


def _positions_with_seed(
    deps: GraphDeps, positions: list[PositionRow]
) -> list[tuple[str, str, str]]:
    values: list[tuple[str, str, str]] = []
    for position in positions:
        seed_entity_id = deps.repos.runs.get_seed_entity_id(position.id)
        if seed_entity_id is not None:
            values.append((position.id, position.symbol, seed_entity_id))
    return values


def _brief_position_response(
    position: PositionRow, deps: GraphDeps
) -> BriefPositionResponse:
    thesis = deps.repos.theses.latest_for_position(position.id)
    return BriefPositionResponse(
        position_id=position.id,
        symbol=position.symbol,
        name=position.name,
        thesis_summary=thesis.summary if thesis is not None else None,
        thesis_status=thesis.status if thesis is not None else None,
    )


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
