import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from types import ModuleType

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.graph.runner import build_graph_deps
from noesis.graph.state import GraphDeps
from noesis.tools.llm.fake import FakeLLMRouter
from noesis.tools.search.fake import FakeSearchAdapter

NOW = "2026-06-28T00:00:00Z"
LATEST = "2026-06-28T00:01:00Z"


def test_eval_basis_honesty_uses_edge_evidence_across_runs(tmp_path: Path) -> None:
    module = _load_eval_module()
    conn = connect(tmp_path / "noesis.db")
    checkpoint_conn = sqlite3.connect(tmp_path / "checkpoints.db", check_same_thread=False)
    try:
        migrate(conn)
        _seed_runs(conn, edge_evidence_ids=("evidence-old",))
        report = module.evaluate_existing_runs(
            (module.EvalCase(symbol="AAPL", market="US", name="Apple Inc."),),
            _deps(conn, checkpoint_conn, tmp_path),
        )

        assert report.results[0].run_id == "run-latest"
        assert report.results[0].metrics["basis_honesty"] == 1.0
        assert report.results[0].metrics["grounding_rate"] == 1.0
    finally:
        checkpoint_conn.close()
        conn.close()


def test_eval_basis_honesty_still_fails_for_missing_edge_evidence(
    tmp_path: Path,
) -> None:
    module = _load_eval_module()
    conn = connect(tmp_path / "noesis.db")
    checkpoint_conn = sqlite3.connect(tmp_path / "checkpoints.db", check_same_thread=False)
    try:
        migrate(conn)
        _seed_runs(conn, edge_evidence_ids=("missing-edge-evidence",))
        report = module.evaluate_existing_runs(
            (module.EvalCase(symbol="AAPL", market="US", name="Apple Inc."),),
            _deps(conn, checkpoint_conn, tmp_path),
        )

        assert report.results[0].metrics["basis_honesty"] == 0.0
    finally:
        checkpoint_conn.close()
        conn.close()


def _deps(
    conn: sqlite3.Connection,
    checkpoint_conn: sqlite3.Connection,
    tmp_path: Path,
) -> GraphDeps:
    return build_graph_deps(
        conn=conn,
        checkpoint_conn=checkpoint_conn,
        chroma_dir=str(tmp_path / "chroma"),
        search=FakeSearchAdapter([]),
        llm=FakeLLMRouter(),
        now=lambda: NOW,
    )


def _load_eval_module() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "eval.py"
    spec = importlib.util.spec_from_file_location("eval_script_edge", path)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load eval.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["eval_script_edge"] = module
    spec.loader.exec_module(module)
    return module


def _seed_runs(conn: sqlite3.Connection, edge_evidence_ids: tuple[str, ...]) -> None:
    with with_tx(conn):
        conn.execute("PRAGMA defer_foreign_keys = ON")
        _insert_entity(conn, "entity-aapl", "company", "Apple Inc.", ["Apple"], {"symbol": "AAPL"})
        _insert_entity(conn, "entity-tsm", "company", "TSMC", [], {"symbol": "TSM"})
        _insert_position(conn)
        _insert_run(conn, "run-old", NOW)
        _insert_run(conn, "run-latest", LATEST)
        _insert_evidence(conn, "evidence-old", "run-old")
        _insert_evidence(conn, "evidence-latest", "run-latest")
        _insert_intel(conn, "intel-latest", "run-latest", "evidence-latest")
        _insert_thesis(conn, "thesis-latest", "run-latest", "evidence-latest")
        _insert_edge(conn, edge_evidence_ids)


def _insert_entity(
    conn: sqlite3.Connection,
    id: str,
    node_type: str,
    name: str,
    aliases: list[str],
    identifiers: dict[str, str],
) -> None:
    conn.execute(
        """
        INSERT INTO entities(
          id, node_type, name, aliases_json, identifiers_json, market,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            id,
            node_type,
            name,
            json.dumps(aliases),
            json.dumps(identifiers),
            "US",
            NOW,
            NOW,
        ),
    )


def _insert_position(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO positions(
          id, user_id, symbol, market, name, kind, qty, cost_basis,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("position-aapl", "local-user", "AAPL", "US", "Apple Inc.", "owned", None, None, NOW, NOW),
    )


def _insert_run(conn: sqlite3.Connection, run_id: str, at: str) -> None:
    conn.execute(
        """
        INSERT INTO run_registry(
          id, position_id, entity_id, node_kind, status, started_at,
          ended_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, "position-aapl", "entity-aapl", "seed", "completed", at, at, at),
    )


def _insert_evidence(conn: sqlite3.Connection, evidence_id: str, run_id: str) -> None:
    conn.execute(
        """
        INSERT INTO evidences(
          id, run_id, entity_id, source, source_tier, url, title, snippet,
          captured_at, published_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            evidence_id,
            run_id,
            "entity-aapl",
            "web",
            2,
            f"https://example.com/{evidence_id}",
            "Apple evidence",
            "Apple evidence snippet.",
            NOW,
            None,
            NOW,
        ),
    )


def _insert_intel(
    conn: sqlite3.Connection, intel_id: str, run_id: str, evidence_id: str
) -> None:
    conn.execute(
        """
        INSERT INTO intel_items(
          id, entity_id, run_id, source, source_tier, title, content, url,
          published_at, sentiment_json, event_type, evidence_ids_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            intel_id,
            "entity-aapl",
            run_id,
            "web",
            2,
            "Apple supplier update",
            "Apple supplier pressure eased.",
            f"https://example.com/{evidence_id}",
            None,
            json.dumps({"dir": "neutral", "conf": 0.8}),
            "news",
            json.dumps([evidence_id]),
            NOW,
        ),
    )


def _insert_thesis(
    conn: sqlite3.Connection, thesis_id: str, run_id: str, evidence_id: str
) -> None:
    conn.execute(
        """
        INSERT INTO theses(id, position_id, run_id, summary, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (thesis_id, "position-aapl", run_id, "Apple supplier thesis.", "confirmed", NOW, NOW),
    )
    conn.execute(
        """
        INSERT INTO thesis_assumptions(
          id, thesis_id, text, kind, evidence_ids_json, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "assumption-latest",
            thesis_id,
            "Apple assumption with evidence.",
            "assumption",
            json.dumps([evidence_id]),
            "active",
            NOW,
        ),
    )


def _insert_edge(conn: sqlite3.Connection, evidence_ids: tuple[str, ...]) -> None:
    conn.execute(
        """
        INSERT INTO graph_edges(
          id, from_entity_id, to_entity_id, relation, basis, confidence,
          evidence_ids_json, run_id, rationale, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "edge-1",
            "entity-aapl",
            "entity-tsm",
            "supplier",
            "source_backed",
            0.8,
            json.dumps(list(evidence_ids)),
            "run-old",
            "TSMC cited as supplier.",
            NOW,
        ),
    )
