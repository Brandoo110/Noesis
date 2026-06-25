from uuid import uuid4

from fastapi import APIRouter, Depends, status

from noesis.api.deps import get_graph_deps
from noesis.api.dto import CreatePositionRequest, PositionResponse
from noesis.db.connection import with_tx
from noesis.db.models import PositionRow
from noesis.graph.state import GraphDeps

router = APIRouter(prefix="/positions", tags=["positions"])


@router.post(
    "",
    response_model=PositionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_position(
    request: CreatePositionRequest,
    deps: GraphDeps = Depends(get_graph_deps),
) -> PositionResponse:
    now = deps.now()
    row = PositionRow(
        id=f"position-{uuid4().hex}",
        user_id="local-user",
        symbol=request.symbol,
        market=request.market,
        name=request.name,
        kind=request.kind,
        qty=request.qty,
        cost_basis=request.cost_basis,
        created_at=now,
        updated_at=now,
    )
    with with_tx(deps.repos.conn):
        deps.repos.positions.insert(row)
    return PositionResponse(
        id=row.id,
        symbol=row.symbol,
        market=row.market,
        name=row.name,
        kind=row.kind,
        qty=row.qty,
        cost_basis=row.cost_basis,
    )
