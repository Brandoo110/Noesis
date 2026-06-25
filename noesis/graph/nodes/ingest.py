from noesis.graph.errors import IngestError
from noesis.graph.schemas import DegradeNote, ResolvedEntity
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate

REQUIRED_STATE_KEYS = ("resolved_entity",)
OUTPUT_STATE_KEYS = ("ingested_docs", "degraded")


def ingest(state: ResearchState, deps: GraphDeps) -> ResearchStateUpdate:
    entity = state.get("resolved_entity")
    if entity is None:
        raise IngestError("resolved_entity is required", reason="missing_resolved_entity")
    degraded = list(state.get("degraded", []))
    try:
        docs = deps.search.search(_query(entity), limit=8)
    except IngestError as exc:
        degraded.append(
            DegradeNote(
                node_name="ingest",
                reason=exc.reason or "search_failed",
                fallback_used="empty_docs",
            )
        )
        return {"ingested_docs": [], "degraded": degraded}
    return {"ingested_docs": docs, "degraded": degraded}


def _query(entity: ResolvedEntity) -> str:
    symbol = entity.identifiers.get("symbol")
    if symbol:
        return f"{entity.name} {symbol} stock latest news earnings results"
    return f"{entity.name} stock latest news earnings results"
