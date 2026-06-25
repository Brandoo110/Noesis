from pathlib import Path
from sqlite3 import Connection

from noesis.db.connection import connect
from noesis.db.migrate import migrate
from noesis.graph.schemas import EvidenceRecord
from noesis.tools.retrieval.store import EvidenceRetriever


NOW = "2026-06-26T00:00:00Z"


def make_evidence(id: str, snippet: str, run_id: str = "run-1") -> EvidenceRecord:
    return EvidenceRecord(
        id=id,
        source="web",
        source_tier=2,
        url=f"https://example.com/{id}",
        title=f"Title {id}",
        snippet=snippet,
        captured_at=NOW,
        published_at=None,
    )


def test_evidence_retriever_indexes_and_retrieves_known_evidence(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "retrieval.db"
    chroma_dir = tmp_path / "chroma"
    conn = connect(db_path)
    migrate(conn)
    try:
        retriever = EvidenceRetriever(str(chroma_dir), lambda: conn)
        evidences = [
            make_evidence("evidence-1", "Apple supplier capacity expands."),
            make_evidence("evidence-2", "Microsoft cloud revenue grows."),
            make_evidence("evidence-3", "Battery supply chain pressure eases."),
        ]

        retriever.index(evidences)
        results = retriever.retrieve("battery pressure", run_id="run-1", top_k=2)
    finally:
        conn.close()

    assert results[0].id == "evidence-3"
    assert results[0].snippet == "Battery supply chain pressure eases."
    assert {item.id for item in results}.issubset({item.id for item in evidences})
