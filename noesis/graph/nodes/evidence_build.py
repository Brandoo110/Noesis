import hashlib
from urllib.parse import urlparse

from noesis.db.connection import with_tx
from noesis.db.models import SourceDocumentRow
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
    docs = state.get("filtered_docs", [])
    evidences = _build_evidences(
        docs,
        run_id=run_id,
        entity_id=entity_id,
        captured_at=deps.now(),
    )
    degraded = list(state.get("degraded", []))
    try:
        _record_source_documents(
            docs,
            run_id=run_id,
            entity_id=entity_id,
            fetched_at=deps.now(),
            deps=deps,
        )
    except Exception:
        degraded.append(
            DegradeNote(
                node_name="evidence_build",
                reason="source_document_persist_failed",
                fallback_used="evidence_without_source_document_row",
            )
        )
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


def _record_source_documents(
    docs: list[IngestedDoc],
    *,
    run_id: str,
    entity_id: str,
    fetched_at: str,
    deps: GraphDeps,
) -> None:
    source_documents_repo = getattr(deps.repos, "source_documents", None)
    conn = getattr(deps.repos, "conn", None)
    if source_documents_repo is None or conn is None:
        return
    rows = _build_source_documents(
        docs,
        run_id=run_id,
        entity_id=entity_id,
        fetched_at=fetched_at,
    )
    if not rows:
        return
    with with_tx(conn):
        source_documents_repo.insert_many(rows, conn=conn)


def _build_source_documents(
    docs: list[IngestedDoc], *, run_id: str, entity_id: str, fetched_at: str
) -> list[SourceDocumentRow]:
    seen: set[str] = set()
    rows: list[SourceDocumentRow] = []
    for doc in docs:
        key = _dedupe_key(doc)
        if key in seen:
            continue
        seen.add(key)
        content_hash = _content_hash(doc.text)
        rows.append(
            SourceDocumentRow(
                id=f"source-doc-{_digest(run_id, entity_id, key)}",
                run_id=run_id,
                entity_id=entity_id,
                url=doc.url,
                title=doc.title,
                publisher=_publisher(doc.url),
                published_at=doc.published_at,
                fetched_at=fetched_at,
                source_type=doc.source,
                reliability=_reliability(doc.source_tier),
                content_hash=content_hash,
                source_tier=doc.source_tier,
                created_at=fetched_at,
            )
        )
    return rows


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


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _publisher(url: str | None) -> str | None:
    if not url:
        return None
    host = urlparse(url).netloc.lower()
    return host or None


def _reliability(source_tier: int) -> float:
    if source_tier <= 1:
        return 1.0
    if source_tier == 2:
        return 0.8
    return 0.55


def _digest(*parts: str) -> str:
    joined = "|".join(parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]
