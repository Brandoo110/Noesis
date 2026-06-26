from dataclasses import dataclass

from noesis.graph.nodes.expand import expand
from noesis.graph.schemas import EvidenceRecord, GraphEdgeDraft, ResolvedEntity
from noesis.graph.state import GraphDeps, ResearchState
from noesis.tools.llm.fake import FakeLLMRouter
from noesis.tools.llm.router import LLMRole

NOW = "2026-06-26T00:00:00Z"


@dataclass
class EmptyRepos:
    pass


def make_entity() -> ResolvedEntity:
    return ResolvedEntity(
        entity_id="entity-aapl",
        node_type="company",
        name="Apple Inc.",
        aliases=["AAPL"],
        identifiers={"symbol": "AAPL"},
        market="US",
    )


def make_evidence(id: str = "evidence-1") -> EvidenceRecord:
    return EvidenceRecord(
        id=id,
        run_id="run-1",
        source="web",
        source_tier=2,
        url=f"https://example.com/{id}",
        title="Evidence",
        snippet="Apple cites this company in its supply chain.",
        captured_at=NOW,
    )


def make_edge(
    name: str,
    *,
    confidence: float,
    evidence_ids: list[str] | None = None,
    basis: str = "source_backed",
) -> dict[str, object]:
    return {
        "to_name": name,
        "to_symbol": name[:4].upper(),
        "to_node_type": "company",
        "relation": "supplier",
        "basis": basis,
        "confidence": confidence,
        "evidence_ids": ["evidence-1"] if evidence_ids is None else evidence_ids,
        "rationale": f"{name} is linked to Apple supply chain evidence.",
    }


def make_deps(llm: FakeLLMRouter) -> GraphDeps:
    return GraphDeps(
        repos=EmptyRepos(),
        search=object(),
        retriever=object(),
        llm=llm,
        now=lambda: NOW,
    )


def test_expand_returns_valid_top_five_edges() -> None:
    state: ResearchState = {
        "resolved_entity": make_entity(),
        "evidences": [make_evidence("evidence-1")],
        "degraded": [],
    }
    deps = make_deps(
        FakeLLMRouter(
            json_by_role={
                LLMRole.SYNTH: {
                    "edges": [
                        make_edge("Low", confidence=0.1),
                        make_edge("TSMC", confidence=0.9),
                        make_edge("Foxconn", confidence=0.8),
                        make_edge("Samsung", confidence=0.7),
                        make_edge("Sony", confidence=0.6),
                        make_edge("Broadcom", confidence=0.5),
                    ]
                }
            }
        )
    )

    update = expand(state, deps)

    assert [edge.to_name for edge in update["graph_edges"]] == [
        "TSMC",
        "Foxconn",
        "Samsung",
        "Sony",
        "Broadcom",
    ]
    assert update["graph_edges"][0] == GraphEdgeDraft(
        to_name="TSMC",
        to_symbol="TSMC",
        to_node_type="company",
        relation="supplier",
        basis="source_backed",
        confidence=0.9,
        evidence_ids=["evidence-1"],
        rationale="TSMC is linked to Apple supply chain evidence.",
    )
    assert update["degraded"] == []


def test_expand_degrades_when_synth_unavailable() -> None:
    state: ResearchState = {
        "resolved_entity": make_entity(),
        "evidences": [make_evidence("evidence-1")],
        "degraded": [],
    }

    update = expand(state, make_deps(FakeLLMRouter(available_roles=set())))

    assert update["graph_edges"] == []
    assert update["degraded"][0].node_name == "expand"
    assert update["degraded"][0].fallback_used == "empty_graph_edges"


def test_expand_filters_invalid_source_backed_edges() -> None:
    state: ResearchState = {
        "resolved_entity": make_entity(),
        "evidences": [make_evidence("evidence-1")],
        "degraded": [],
    }
    deps = make_deps(
        FakeLLMRouter(
            json_by_role={
                LLMRole.SYNTH: {
                    "edges": [
                        make_edge("Grounded", confidence=0.8),
                        make_edge("Ungrounded", confidence=0.9, evidence_ids=[]),
                        make_edge("Inferred", confidence=0.7, evidence_ids=[], basis="inferred"),
                    ]
                }
            }
        )
    )

    update = expand(state, deps)

    assert [edge.to_name for edge in update["graph_edges"]] == ["Grounded", "Inferred"]
    assert update["degraded"][0].reason == "invalid_edge_basis"
    assert update["degraded"][0].fallback_used == "drop_invalid_edges"
