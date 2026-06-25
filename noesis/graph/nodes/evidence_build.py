import hashlib

from noesis.graph.errors import ResearchNodeError
from noesis.graph.schemas import DegradeNote, EvidenceRecord, IngestedDoc
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate

REQUIRED_STATE_KEYS = ("filtered_docs", "run_id", "entity_id")
OUTPUT_STATE_KEYS = ("evidences", "degraded")
MAX_SNIPPET_CHARS = 600


def evidence_build(state: ResearchState, deps: GraphDeps) -> ResearchStateUpdate:
    run_id = state.get("run_id")
    entity_id = state.get("entity_id")
    if run_id is None or entity_id is None:
        raise ResearchNodeError("run_id and entity_id are required", reason="missing_ids")
    evidences = _build_evidences(
        state.get("filtered_docs", []),
        run_id=run_id,
        entity_id=entity_id,
        captured_at=deps.now(),
    )
    degraded = list(state.get("degraded", []))
    try:
        deps.retriever.index(evidences)
    except Exception:
        degraded.append(
            DegradeNote(
                node_name="evidence_build",
                reason="retriever_index_failed",
                fallback_used="evidence_without_vector_index",
            )
        )
    return {"evidences": evidences, "degraded": degraded}


def _build_evidences(
    docs: list[IngestedDoc], *, run_id: str, entity_id: str, captured_at: str
) -> list[EvidenceRecord]:
    seen: set[str] = set()
    evidences: list[EvidenceRecord] = []
    for doc in docs:
        key = _dedupe_key(doc)
        if key in seen:
            continue
        seen.add(key)
        evidence_id = f"evidence-{_digest(run_id, entity_id, key)}"
        evidences.append(
            EvidenceRecord(
                id=evidence_id,
                run_id=run_id,
                source=doc.source,
                source_tier=doc.source_tier,
                url=doc.url,
                title=doc.title,
                snippet=doc.text.strip()[:MAX_SNIPPET_CHARS],
                captured_at=captured_at,
                published_at=doc.published_at,
            )
        )
    return evidences


def _dedupe_key(doc: IngestedDoc) -> str:
    if doc.url:
        return f"url:{doc.url}"
    return f"text:{_digest(doc.text.strip())}"


def _digest(*parts: str) -> str:
    joined = "|".join(parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]
