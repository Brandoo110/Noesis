from noesis.graph.schemas import IngestedDoc
from noesis.graph.state import GraphDeps, ResearchState, ResearchStateUpdate

REQUIRED_STATE_KEYS = ("ingested_docs",)
OUTPUT_STATE_KEYS = ("filtered_docs", "degraded")
MAX_DOC_TEXT_CHARS = 12_000


def filter(state: ResearchState, deps: GraphDeps) -> ResearchStateUpdate:
    docs = state.get("ingested_docs", [])
    filtered = [_trim_doc(doc) for doc in docs if doc.text.strip()]
    return {"filtered_docs": filtered, "degraded": list(state.get("degraded", []))}


def _trim_doc(doc: IngestedDoc) -> IngestedDoc:
    if len(doc.text) <= MAX_DOC_TEXT_CHARS:
        return doc
    return doc.model_copy(update={"text": doc.text[:MAX_DOC_TEXT_CHARS]})
