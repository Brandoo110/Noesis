import re
import sqlite3
from pathlib import Path
from sqlite3 import Connection

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import EntityRow, PositionRow
from noesis.db.repos.entities_repo import EntitiesRepo
from noesis.db.repos.positions_repo import PositionsRepo
from noesis.graph.runner import build_graph_deps, start_expand_run
from noesis.graph.schemas import IngestedDoc
from noesis.tools.llm.router import LLMRole
from noesis.tools.search.fake import FakeSearchAdapter

NOW = "2026-06-26T00:00:00Z"


class ExpandFakeLLM:
    def __init__(self, *, synth_available: bool = True) -> None:
        self.synth_available = synth_available

    def available(self, role: LLMRole) -> bool:
        return role != LLMRole.SYNTH or self.synth_available

    def complete_json(self, role: LLMRole, prompt: str, schema: type) -> object:
        evidence_id = _first_evidence_id(prompt)
        if role == LLMRole.LIGHT:
            return schema.model_validate(
                {
                    "items": [
                        {
                            "title": "Supplier pressure update",
                            "content": "Supplier pressure eased based on cited evidence.",
                            "event_type": "supply_chain",
                            "source": "web",
                            "source_tier": 2,
                            "url": "https://example.com/supplier",
                            "published_at": None,
                            "sentiment": {"dir": "neutral", "conf": 0.7},
                            "evidence_ids": [evidence_id],
                        }
                    ]
                }
            )
        return schema.model_validate(
            {
                "edges": [
                    {
                        "to_name": "Taiwan Semiconductor Manufacturing",
                        "to_symbol": "TSM",
                        "to_node_type": "company",
                        "relation": "supplier",
                        "basis": "source_backed",
                        "confidence": 0.82,
                        "evidence_ids": [evidence_id],
                        "rationale": "Supplier relationship is cited in evidence.",
                    }
                ]
            }
        )

    def complete_text(self, role: LLMRole, prompt: str) -> str:
        return "{}"


def test_start_expand_run_persists_edges_and_uses_cache(tmp_path: Path) -> None:
    conn = make_conn(tmp_path)
    try:
        seed_position_and_entity(conn)
        deps = make_deps(tmp_path, conn, llm=ExpandFakeLLM())

        first = start_expand_run("entity-aapl", "position-1", deps)
        edges = deps.repos.graph_edges.list_from("entity-aapl", conn=conn)
        expansion = deps.repos.node_expansions.get("entity-aapl", conn=conn)
        run_count = _expand_run_count(conn)
        second = start_expand_run("entity-aapl", "position-1", deps)
        cached_count = _expand_run_count(conn)
    finally:
        conn.close()

    assert first.status == "completed"
    assert edges and edges[0].basis == "source_backed"
    assert edges[0].evidence_ids()
    assert expansion is not None and expansion.cached_run_id == first.run_id
    assert second.status == "cached"
    assert second.run_id == first.run_id
    assert cached_count == run_count


def test_start_expand_run_completes_when_synth_unavailable(
    tmp_path: Path,
) -> None:
    conn = make_conn(tmp_path)
    try:
        seed_position_and_entity(conn)
        deps = make_deps(tmp_path, conn, llm=ExpandFakeLLM(synth_available=False))

        handle = start_expand_run("entity-aapl", "position-1", deps)

        edges = deps.repos.graph_edges.list_from("entity-aapl", conn=conn)
        traces = deps.repos.traces.list_by_run(handle.run_id, conn=conn)
    finally:
        conn.close()

    assert handle.status == "completed"
    assert edges == []
    assert any(
        trace.node_name == "expand"
        and trace.status == "degraded"
        and trace.reason == "synth_llm_unavailable"
        for trace in traces
    )


def make_conn(tmp_path: Path) -> Connection:
    conn = connect(tmp_path / "noesis.db")
    migrate(conn)
    return conn


def seed_position_and_entity(conn: Connection) -> None:
    with with_tx(conn):
        PositionsRepo().insert(
            PositionRow(
                id="position-1",
                user_id="user-1",
                symbol="AAPL",
                market="US",
                name="Apple",
                kind="owned",
                qty=None,
                cost_basis=None,
                created_at=NOW,
                updated_at=NOW,
            ),
            conn=conn,
        )
        EntitiesRepo().upsert(
            EntityRow(
                id="entity-aapl",
                node_type="company",
                name="Apple Inc.",
                aliases_json='["AAPL"]',
                identifiers_json='{"symbol": "AAPL"}',
                market="US",
                created_at=NOW,
                updated_at=NOW,
            ),
            conn=conn,
        )


def make_deps(tmp_path: Path, conn: Connection, *, llm: ExpandFakeLLM) -> object:
    docs = [
        IngestedDoc(
            source="web",
            source_tier=2,
            title="Supplier update",
            url="https://example.com/supplier",
            text="Supplier pressure eased for Apple.",
        )
    ]
    return build_graph_deps(
        conn=conn,
        checkpoint_conn=sqlite3.connect(
            tmp_path / "checkpoints.db",
            check_same_thread=False,
        ),
        chroma_dir=str(tmp_path / "chroma"),
        search=FakeSearchAdapter(docs),
        llm=llm,
        now=lambda: NOW,
    )


def _expand_run_count(conn: Connection) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM run_registry WHERE node_kind = ?",
        ("expand",),
    ).fetchone()
    return int(row[0])


def _first_evidence_id(prompt: str) -> str:
    match = re.search(r"(evidence-[a-f0-9]+)", prompt)
    if match is None:
        raise AssertionError(f"prompt did not include evidence id: {prompt}")
    return match.group(1)
