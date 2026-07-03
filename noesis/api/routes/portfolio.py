from fastapi import APIRouter, Depends

from noesis.api.deps import get_graph_deps
from noesis.api.dto import (
    BriefPositionResponse,
    CorrelationCellResponse,
    CorrelationMatrixResponse,
    MatrixAxisResponse,
    OverlapGroupResponse,
    OverlapPositionResponse,
    PortfolioBriefResponse,
    SharedPositionResponse,
    SharedSupplierGroupResponse,
)
from noesis.api.portfolio_health import run_health_response
from noesis.api.position_rows import dedupe_positions, position_label
from noesis.db.models import PositionRow
from noesis.graph.state import GraphDeps
from noesis.graph.traversal import (
    CorrelationMatrix,
    OverlapGroup,
    SharedSupplierGroup,
    portfolio_overlap,
    shared_supply_chain,
    supply_chain_correlation,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/overlaps", response_model=list[OverlapGroupResponse])
def get_portfolio_overlaps(
    deps: GraphDeps = Depends(get_graph_deps),
) -> list[OverlapGroupResponse]:
    positions = dedupe_positions(deps.repos.positions.list_by_user("local-user"), deps)
    return [
        _overlap_response(group)
        for group in _portfolio_overlap_groups(deps, positions)
    ]


@router.get("/shared-suppliers", response_model=list[SharedSupplierGroupResponse])
def get_portfolio_shared_suppliers(
    deps: GraphDeps = Depends(get_graph_deps),
) -> list[SharedSupplierGroupResponse]:
    positions = dedupe_positions(deps.repos.positions.list_by_user("local-user"), deps)
    symbols_by_position = _position_symbols(positions)
    return [
        _shared_supplier_response(group, symbols_by_position)
        for group in shared_supply_chain(
            _positions_with_seed(deps, positions),
            deps.repos.graph_edges,
            deps.repos.entities,
        )
    ]


@router.get("/correlation", response_model=CorrelationMatrixResponse)
def get_portfolio_correlation(
    deps: GraphDeps = Depends(get_graph_deps),
) -> CorrelationMatrixResponse:
    positions = dedupe_positions(deps.repos.positions.list_by_user("local-user"), deps)
    matrix = supply_chain_correlation(
        _positions_with_seed(deps, positions),
        deps.repos.graph_edges,
        deps.repos.entities,
    )
    return _correlation_response(matrix, _position_symbols(positions))


@router.get("/brief", response_model=PortfolioBriefResponse)
def get_portfolio_brief(
    deps: GraphDeps = Depends(get_graph_deps),
) -> PortfolioBriefResponse:
    positions = dedupe_positions(deps.repos.positions.list_by_user("local-user"), deps)
    return PortfolioBriefResponse(
        generated_at=deps.now(),
        positions=[_brief_position_response(position, deps) for position in positions],
        overlaps=[
            _overlap_response(group)
            for group in _portfolio_overlap_groups(deps, positions)
        ],
        run_health=run_health_response(deps, positions),
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
            values.append((position.id, position_label(position), seed_entity_id))
    return values


def _position_symbols(positions: list[PositionRow]) -> dict[str, str | None]:
    return {position.id: position.symbol or None for position in positions}


def _brief_position_response(
    position: PositionRow, deps: GraphDeps
) -> BriefPositionResponse:
    thesis = deps.repos.theses.latest_for_position(position.id)
    if thesis is not None and _is_eval_placeholder_summary(thesis.summary):
        thesis = None
    return BriefPositionResponse(
        position_id=position.id,
        symbol=position_label(position),
        name=position.name,
        thesis_summary=thesis.summary if thesis is not None else None,
        thesis_status=thesis.status if thesis is not None else None,
    )


def _is_eval_placeholder_summary(summary: str) -> bool:
    return summary.strip().endswith(" has evidence-backed research context.")


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


def _shared_supplier_response(
    group: SharedSupplierGroup,
    symbols_by_position: dict[str, str | None],
) -> SharedSupplierGroupResponse:
    return SharedSupplierGroupResponse(
        supplier_id=group.supplier_id,
        supplier_name=group.supplier_name,
        node_type=group.node_type,
        basis=group.basis,
        positions=[
            SharedPositionResponse(
                position_id=position.position_id,
                symbol=symbols_by_position.get(position.position_id, position.symbol),
                entity_id=position.entity_id,
                confidence=position.confidence,
            )
            for position in group.positions
        ],
    )


def _correlation_response(
    matrix: CorrelationMatrix,
    symbols_by_position: dict[str, str | None],
) -> CorrelationMatrixResponse:
    return CorrelationMatrixResponse(
        positions=[
            MatrixAxisResponse(
                position_id=axis.position_id,
                symbol=symbols_by_position.get(axis.position_id, axis.symbol),
                label=axis.label,
            )
            for axis in matrix.positions
        ],
        cells=[
            CorrelationCellResponse(
                a_position_id=cell.a_position_id,
                b_position_id=cell.b_position_id,
                shared_count=cell.shared_count,
                shared_suppliers=cell.shared_suppliers,
            )
            for cell in matrix.cells
        ],
    )
