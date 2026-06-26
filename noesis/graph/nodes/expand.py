from pydantic import BaseModel

from noesis.graph.errors import LLMUnavailableError, ResearchNodeError
from noesis.graph.grounding import filter_valid_edges
from noesis.graph.schemas import (
    DegradeNote,
    EvidenceRecord,
    GraphEdgeDraft,
    ResolvedEntity,
)
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate
from noesis.tools.llm.router import LLMRole

REQUIRED_STATE_KEYS = ("resolved_entity", "evidences")
OUTPUT_STATE_KEYS = ("graph_edges", "degraded")
MAX_EDGES = 5


class ExpandPayload(BaseModel):
    edges: list[GraphEdgeDraft]


def expand(state: ResearchState, deps: GraphDeps) -> ResearchStateUpdate:
    entity = state.get("resolved_entity")
    if entity is None:
        raise ResearchNodeError("resolved_entity is required", reason="missing_resolved_entity")
    evidences = state.get("evidences", [])
    degraded = list(state.get("degraded", []))
    if not deps.llm.available(LLMRole.SYNTH):
        degraded.append(_degrade("synth_llm_unavailable", "empty_graph_edges"))
        return {"graph_edges": [], "degraded": degraded}
    try:
        payload = deps.llm.complete_json(
            LLMRole.SYNTH,
            _prompt(entity, evidences),
            ExpandPayload,
        )
    except (LLMUnavailableError, ResearchNodeError) as exc:
        degraded.append(_degrade(exc.reason or "llm_failed", "empty_graph_edges"))
        return {"graph_edges": [], "degraded": degraded}
    valid_edges = filter_valid_edges(payload.edges, evidences)
    if len(valid_edges) != len(payload.edges):
        degraded.append(_degrade("invalid_edge_basis", "drop_invalid_edges"))
    return {
        "graph_edges": _top_edges(valid_edges),
        "degraded": degraded,
    }


def _prompt(entity: ResolvedEntity, evidences: list[EvidenceRecord]) -> str:
    evidence_text = "\n".join(f"- {item.id}: {item.snippet}" for item in evidences)
    symbol = entity.identifiers.get("symbol") or ""
    return (
        "Extract supply-chain graph edges for the target entity only. "
        "Allowed relations are supplier, customer, competitor, and belongs_to. "
        "Do not recommend investments, forecast prices, or discuss trading. "
        "Use basis='source_backed' only when citing provided evidence_ids; "
        "use basis='inferred' for uncited plausible edges with confidence. "
        "Return at most strong candidate edges.\n"
        f"Target: name={entity.name}; symbol={symbol}; market={entity.market or ''}; "
        f"type={entity.node_type}\nEvidence:\n{evidence_text}"
    )


def _top_edges(edges: list[GraphEdgeDraft]) -> list[GraphEdgeDraft]:
    return sorted(edges, key=lambda edge: edge.confidence, reverse=True)[:MAX_EDGES]


def _degrade(reason: str, fallback_used: str) -> DegradeNote:
    return DegradeNote(
        node_name="expand",
        reason=reason,
        fallback_used=fallback_used,
    )
