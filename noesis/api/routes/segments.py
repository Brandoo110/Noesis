from fastapi import APIRouter, Depends

from noesis.api.deps import get_graph_deps
from noesis.api.dto import RepresentativeStockResponse, RepresentativesResponse
from noesis.graph.state import GraphDeps
from noesis.graph.traversal import representative_stocks

router = APIRouter(prefix="/segments", tags=["segments"])


@router.get("/{segment_id}/representatives", response_model=RepresentativesResponse)
def list_representatives(
    segment_id: str,
    top_n: int = 5,
    deps: GraphDeps = Depends(get_graph_deps),
) -> RepresentativesResponse:
    refs = representative_stocks(
        segment_id,
        deps.repos.graph_edges,
        deps.repos.entities,
        top_n=top_n,
    )
    return RepresentativesResponse(
        segment_id=segment_id,
        representatives=[
            RepresentativeStockResponse(
                id=item.id,
                name=item.name,
                symbol=item.symbol,
            )
            for item in refs
        ],
    )
