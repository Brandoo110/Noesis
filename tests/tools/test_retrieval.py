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
        run_id=run_id,
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


def test_evidence_retriever_filters_results_by_run_id(tmp_path: Path) -> None:
    db_path = tmp_path / "retrieval.db"
    chroma_dir = tmp_path / "chroma"
    conn = connect(db_path)
    migrate(conn)
    try:
        retriever = EvidenceRetriever(str(chroma_dir), lambda: conn)
        retriever.index(
            [
                make_evidence(
                    "run-1-evidence",
                    "Battery pressure is easing for suppliers.",
                    run_id="run-1",
                ),
                make_evidence(
                    "run-2-evidence",
                    "Battery pressure is increasing for suppliers.",
                    run_id="run-2",
                ),
            ]
        )

        results = retriever.retrieve("battery pressure", run_id="run-1", top_k=5)
    finally:
        conn.close()

    assert [item.id for item in results] == ["run-1-evidence"]
    assert {item.run_id for item in results} == {"run-1"}


def test_evidence_retriever_falls_back_to_fts_when_chroma_unavailable(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "retrieval.db"
    chroma_dir = tmp_path / "chroma"
    conn = connect(db_path)
    migrate(conn)
    try:
        retriever = EvidenceRetriever(str(chroma_dir), lambda: conn)
        retriever.collection = None
        retriever.index(
            [
                make_evidence(
                    "fts-evidence",
                    "Semiconductor demand pressure has eased.",
                    run_id="run-1",
                )
            ]
        )

        results = retriever.retrieve("semiconductor pressure", run_id="run-1")
    finally:
        conn.close()

    assert [item.id for item in results] == ["fts-evidence"]
    assert results[0].run_id == "run-1"
