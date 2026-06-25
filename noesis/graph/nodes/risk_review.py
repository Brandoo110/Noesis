from noesis.graph.grounding import (
    check_investment_redlines,
    check_intel,
    check_thesis,
    filter_grounded_intel,
    thesis_is_grounded,
)
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate

REQUIRED_STATE_KEYS = ("intel_items", "thesis_draft", "evidences")
OUTPUT_STATE_KEYS = ("risk_findings", "intel_items", "thesis_draft", "degraded")


def risk_review(state: ResearchState, deps: GraphDeps) -> ResearchStateUpdate:
    evidences = state.get("evidences", [])
    intel_items = state.get("intel_items", [])
    thesis_draft = state.get("thesis_draft")
    findings = [
        *check_intel(intel_items, evidences),
        *check_thesis(thesis_draft, evidences),
        *check_investment_redlines(thesis_draft),
    ]
    filtered_intel = filter_grounded_intel(intel_items, evidences)
    redline_findings = check_investment_redlines(thesis_draft)
    filtered_thesis = (
        thesis_draft
        if thesis_is_grounded(thesis_draft, evidences) and not redline_findings
        else None
    )
    return {
        "risk_findings": findings,
        "intel_items": filtered_intel,
        "thesis_draft": filtered_thesis,
        "degraded": list(state.get("degraded", [])),
    }
