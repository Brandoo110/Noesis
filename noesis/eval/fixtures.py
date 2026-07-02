from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from hashlib import sha256

from noesis.db.connection import with_tx
from noesis.eval.cases import EvalCase
from noesis.graph.state import GraphDeps


def seed_eval_fixture_runs(cases: Sequence[EvalCase], deps: GraphDeps) -> None:
    with with_tx(deps.repos.conn):
        for case in cases:
            if _has_seed_run(case, deps.repos.conn):
                _ensure_fixture_source_document(case, deps.repos.conn, deps.now())
                continue
            _insert_case(case, deps.repos.conn, deps.now())


def _has_seed_run(case: EvalCase, conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        """
        SELECT run_registry.id FROM run_registry
        JOIN positions ON positions.id = run_registry.position_id
        WHERE upper(positions.symbol) = ?
          AND positions.market = ?
          AND run_registry.node_kind = 'seed'
        LIMIT 1
        """,
        (case.symbol.upper(), case.market),
    ).fetchone()
    return row is not None


def _insert_case(case: EvalCase, conn: sqlite3.Connection, now: str) -> None:
    suffix = _suffix(case)
    position_id = f"position-eval-{suffix}"
    entity_id = f"entity-eval-{suffix}"
    related_id = f"entity-eval-related-{suffix}"
    run_id = f"run-eval-{suffix}"
    evidence_id = f"evidence-eval-{suffix}"
    thesis_id = f"thesis-{run_id}"
    edge_id = f"edge-eval-{suffix}"
    _insert_entity(conn, entity_id, case.name, case.symbol, now)
    _insert_entity(conn, related_id, _related_name(case), f"{case.symbol}-REL", now)
    _insert_position(conn, position_id, case, now)
    _insert_run(conn, run_id, position_id, entity_id, now)
    _insert_source_document(conn, f"source-doc-eval-{suffix}", run_id, entity_id, case, now)
    _insert_evidence(conn, evidence_id, run_id, entity_id, case, now)
    _insert_intel(conn, run_id, entity_id, evidence_id, case, now)
    _insert_thesis(conn, thesis_id, position_id, run_id, evidence_id, case, now)
    _insert_edge(conn, edge_id, entity_id, related_id, run_id, evidence_id, case, now)
    _insert_trace(conn, f"trace-eval-{suffix}", run_id, entity_id, evidence_id, now)


def _ensure_fixture_source_document(
    case: EvalCase, conn: sqlite3.Connection, now: str
) -> None:
    suffix = _suffix(case)
    run_id = f"run-eval-{suffix}"
    row = conn.execute(
        "SELECT entity_id FROM run_registry WHERE id = ? LIMIT 1", (run_id,)
    ).fetchone()
    if row is None:
        return
    _insert_source_document(
        conn,
        f"source-doc-eval-{suffix}",
        run_id,
        row[0],
        case,
        now,
    )


def _insert_entity(
    conn: sqlite3.Connection, id: str, name: str, symbol: str, now: str
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO entities(
          id, node_type, name, aliases_json, identifiers_json, market,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            id,
            "company",
            name,
            json.dumps([symbol]),
            json.dumps({"symbol": symbol}),
            "US",
            now,
            now,
        ),
    )


def _insert_position(
    conn: sqlite3.Connection, position_id: str, case: EvalCase, now: str
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO positions(
          id, user_id, symbol, market, name, kind, qty, cost_basis,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            position_id,
            "local-user",
            case.symbol,
            case.market,
            case.name,
            "watching",
            None,
            None,
            now,
            now,
        ),
    )


def _insert_run(
    conn: sqlite3.Connection, run_id: str, position_id: str, entity_id: str, now: str
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO run_registry(
          id, position_id, entity_id, node_kind, status, started_at,
          ended_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, position_id, entity_id, "seed", "completed", now, now, now),
    )


def _insert_source_document(
    conn: sqlite3.Connection, source_document_id: str, run_id: str,
    entity_id: str, case: EvalCase, now: str
) -> None:
    snippet = f"{case.name} has fixture evidence for {case.task_type} research."
    conn.execute(
        """
        INSERT OR IGNORE INTO source_documents(
          id, run_id, entity_id, url, title, publisher, published_at,
          fetched_at, source_type, reliability, content_hash, source_tier,
          created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_document_id,
            run_id,
            entity_id,
            f"https://example.com/eval/{case.symbol.lower()}",
            f"{case.name} fixture evidence",
            "example.com",
            now,
            now,
            "fixture",
            0.8,
            sha256(snippet.encode("utf-8")).hexdigest(),
            2,
            now,
        ),
    )


def _insert_evidence(
    conn: sqlite3.Connection, evidence_id: str, run_id: str,
    entity_id: str, case: EvalCase, now: str
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO evidences(
          id, run_id, entity_id, source, source_tier, url, title, snippet,
          captured_at, published_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            evidence_id,
            run_id,
            entity_id,
            "fixture",
            2,
            f"https://example.com/eval/{case.symbol.lower()}",
            f"{case.name} fixture evidence",
            f"{case.name} has fixture evidence for {case.task_type} research.",
            now,
            now,
            now,
        ),
    )


def _insert_intel(
    conn: sqlite3.Connection, run_id: str, entity_id: str,
    evidence_id: str, case: EvalCase, now: str
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO intel_items(
          id, entity_id, run_id, source, source_tier, title, content, url,
          published_at, sentiment_json, event_type, evidence_ids_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"intel-{run_id}",
            entity_id,
            run_id,
            "fixture",
            2,
            f"{case.name} {case.task_type} update",
            f"{case.name} fixture update is grounded in cited evidence.",
            f"https://example.com/eval/{case.symbol.lower()}",
            now,
            json.dumps({"dir": "neutral", "conf": 0.7}),
            case.task_type,
            json.dumps([evidence_id]),
            now,
        ),
    )


def _insert_thesis(
    conn: sqlite3.Connection, thesis_id: str, position_id: str,
    run_id: str, evidence_id: str, case: EvalCase, now: str
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO theses(
          id, position_id, run_id, summary, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            thesis_id,
            position_id,
            run_id,
            f"{case.name} has evidence-backed research context.",
            "confirmed",
            now,
            now,
        ),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO thesis_assumptions(
          id, thesis_id, text, kind, evidence_ids_json, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"assumption-{run_id}",
            thesis_id,
            f"{case.name} assumption remains tied to fixture evidence.",
            "assumption",
            json.dumps([evidence_id]),
            "active",
            now,
        ),
    )


def _insert_edge(
    conn: sqlite3.Connection, edge_id: str, entity_id: str, related_id: str,
    run_id: str, evidence_id: str, case: EvalCase, now: str
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO graph_edges(
          id, from_entity_id, to_entity_id, relation, basis, confidence,
          evidence_ids_json, run_id, rationale, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            edge_id,
            entity_id,
            related_id,
            _relation(case),
            "source_backed",
            0.8,
            json.dumps([evidence_id]),
            run_id,
            "Fixture relationship is backed by fixture evidence.",
            now,
        ),
    )


def _insert_trace(
    conn: sqlite3.Connection, trace_id: str, run_id: str,
    entity_id: str, evidence_id: str, now: str
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO node_traces(
          id, run_id, node_name, entity_id, inputs_ref, outputs_ref, status,
          reason, fallback_used, model_id, evidence_ids_json, started_at,
          ended_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            trace_id,
            run_id,
            "eval_fixture",
            entity_id,
            "fixture",
            "completed",
            "success",
            None,
            None,
            "fixture",
            json.dumps([evidence_id]),
            now,
            now,
            now,
        ),
    )


def _relation(case: EvalCase) -> str:
    if case.task_type == "competitor":
        return "competitor"
    if case.task_type == "supply_chain":
        return "supplier"
    return "belongs_to"


def _related_name(case: EvalCase) -> str:
    if case.task_type == "competitor":
        return f"{case.name} peer"
    if case.task_type == "supply_chain":
        return f"{case.name} supplier"
    return f"{case.name} research context"


def _suffix(case: EvalCase) -> str:
    return case.symbol.lower().replace(".", "-")
