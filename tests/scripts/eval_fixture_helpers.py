import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from types import ModuleType

from noesis.db.connection import with_tx
from noesis.db.models import (
    EntityRow,
    EvidenceRow,
    GraphEdgeRow,
    IntelItemRow,
    ThesisAssumptionRow,
    ThesisRow,
)

NOW = "2026-06-28T00:00:00Z"


def load_eval_module() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "eval.py"
    spec = importlib.util.spec_from_file_location("eval_script", path)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load eval.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["eval_script"] = module
    spec.loader.exec_module(module)
    return module


def seed_completed_run(conn: sqlite3.Connection) -> None:
    with with_tx(conn):
        conn.execute("PRAGMA defer_foreign_keys = ON")
        _insert_entity(conn, "entity-aapl", "company", "Apple Inc.", ["Apple"], {"symbol": "AAPL"})
        _insert_entity(conn, "entity-tsm", "company", "TSMC", [], {"symbol": "TSM"})
        _insert_position(conn)
        _insert_run(conn)
        _insert_evidence(conn)
        _insert_intel(conn)
        _insert_thesis(conn)
        _insert_edge(conn)
        _insert_trace(conn, "trace-success", "intake_resolve", "success")
        _insert_trace(conn, "trace-degraded", "ingest", "degraded")


def _insert_entity(
    conn: sqlite3.Connection,
    id: str,
    node_type: str,
    name: str,
    aliases: list[str],
    identifiers: dict[str, str],
) -> None:
    row = EntityRow(
        id=id,
        node_type=node_type,
        name=name,
        aliases_json=json.dumps(aliases),
        identifiers_json=json.dumps(identifiers),
        market="US",
        created_at=NOW,
        updated_at=NOW,
    )
    conn.execute(
        """
        INSERT INTO entities(
          id, node_type, name, aliases_json, identifiers_json, market,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.id,
            row.node_type,
            row.name,
            row.aliases_json,
            row.identifiers_json,
            row.market,
            row.created_at,
            row.updated_at,
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


def _insert_run(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO run_registry(
          id, position_id, entity_id, node_kind, status, started_at,
          ended_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("run-aapl", "position-aapl", "entity-aapl", "seed", "completed", NOW, NOW, NOW),
    )


def _insert_evidence(conn: sqlite3.Connection) -> None:
    row = EvidenceRow(
        id="evidence-1",
        run_id="run-aapl",
        entity_id="entity-aapl",
        source="web",
        source_tier=2,
        url="https://example.com/evidence-1",
        title="Apple evidence",
        snippet="Apple evidence snippet.",
        captured_at=NOW,
        published_at=None,
        created_at=NOW,
    )
    conn.execute(
        """
        INSERT INTO evidences(
          id, run_id, entity_id, source, source_tier, url, title, snippet,
          captured_at, published_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.id,
            row.run_id,
            row.entity_id,
            row.source,
            row.source_tier,
            row.url,
            row.title,
            row.snippet,
            row.captured_at,
            row.published_at,
            row.created_at,
        ),
    )


def _insert_intel(conn: sqlite3.Connection) -> None:
    row = IntelItemRow(
        id="intel-1",
        entity_id="entity-aapl",
        run_id="run-aapl",
        source="web",
        source_tier=2,
        title="Apple supplier update",
        content="Apple supplier pressure eased.",
        url="https://example.com/evidence-1",
        published_at=None,
        sentiment_json=json.dumps({"dir": "neutral", "conf": 0.8}),
        event_type="news",
        evidence_ids_json=json.dumps(["evidence-1"]),
        created_at=NOW,
    )
    conn.execute(
        """
        INSERT INTO intel_items(
          id, entity_id, run_id, source, source_tier, title, content, url,
          published_at, sentiment_json, event_type, evidence_ids_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.id,
            row.entity_id,
            row.run_id,
            row.source,
            row.source_tier,
            row.title,
            row.content,
            row.url,
            row.published_at,
            row.sentiment_json,
            row.event_type,
            row.evidence_ids_json,
            row.created_at,
        ),
    )


def _insert_thesis(conn: sqlite3.Connection) -> None:
    thesis = ThesisRow(
        id="thesis-run-aapl",
        position_id="position-aapl",
        run_id="run-aapl",
        summary="Apple supplier pressure is easing.",
        status="confirmed",
        created_at=NOW,
        updated_at=NOW,
    )
    conn.execute(
        """
        INSERT INTO theses(id, position_id, run_id, summary, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            thesis.id,
            thesis.position_id,
            thesis.run_id,
            thesis.summary,
            thesis.status,
            thesis.created_at,
            thesis.updated_at,
        ),
    )
    assumption = ThesisAssumptionRow(
        id="assumption-1",
        thesis_id=thesis.id,
        text="Apple assumption with evidence.",
        kind="assumption",
        evidence_ids_json=json.dumps(["evidence-1"]),
        status="active",
        created_at=NOW,
    )
    conn.execute(
        """
        INSERT INTO thesis_assumptions(
          id, thesis_id, text, kind, evidence_ids_json, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            assumption.id,
            assumption.thesis_id,
            assumption.text,
            assumption.kind,
            assumption.evidence_ids_json,
            assumption.status,
            assumption.created_at,
        ),
    )


def _insert_edge(conn: sqlite3.Connection) -> None:
    edge = GraphEdgeRow(
        id="edge-1",
        from_entity_id="entity-aapl",
        to_entity_id="entity-tsm",
        relation="supplier",
        basis="source_backed",
        confidence=0.8,
        evidence_ids_json=json.dumps(["evidence-1"]),
        run_id="run-aapl",
        rationale="TSMC cited as supplier.",
        created_at=NOW,
    )
    conn.execute(
        """
        INSERT INTO graph_edges(
          id, from_entity_id, to_entity_id, relation, basis, confidence,
          evidence_ids_json, run_id, rationale, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            edge.id,
            edge.from_entity_id,
            edge.to_entity_id,
            edge.relation,
            edge.basis,
            edge.confidence,
            edge.evidence_ids_json,
            edge.run_id,
            edge.rationale,
            edge.created_at,
        ),
    )


def _insert_trace(
    conn: sqlite3.Connection,
    id: str,
    node_name: str,
    status: str,
) -> None:
    conn.execute(
        """
        INSERT INTO node_traces(
          id, run_id, node_name, entity_id, inputs_ref, outputs_ref, status,
          reason, fallback_used, model_id, evidence_ids_json, started_at,
          ended_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            id,
            "run-aapl",
            node_name,
            "entity-aapl",
            "state",
            status,
            status,
            "network unavailable" if status == "degraded" else None,
            "empty_docs" if status == "degraded" else None,
            None,
            json.dumps(["evidence-1"]),
            NOW,
            NOW,
            NOW,
        ),
    )
