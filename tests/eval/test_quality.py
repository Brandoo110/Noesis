import sqlite3
from pathlib import Path

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.eval.quality import build_quality_report, format_quality_report
from tests.scripts.eval_fixture_helpers import NOW, seed_completed_run


def test_quality_report_summarizes_latest_runs_and_evidence_tiers(
    tmp_path: Path,
) -> None:
    conn = _seed_quality_db(tmp_path)
    try:
        report = build_quality_report(conn)
    finally:
        conn.close()

    assert report.status == "blocked"
    assert report.total_positions == 2
    assert report.latest_seed_runs == 2
    assert report.status_counts == {"completed": 1, "failed": 1}
    assert report.evidence_total == 1
    assert report.source_tier_counts == {2: 1}
    assert report.runs_without_evidence == ("run-failed",)
    assert report.runs_without_thesis == ("run-failed",)
    assert report.completed_runs_without_evidence == ()
    assert report.completed_runs_without_thesis == ()
    assert report.pending_runs_without_evidence == ()
    assert report.pending_runs_without_thesis == ()
    assert report.degraded_reason_counts == {"network unavailable": 1}
    assert report.failed_runs == (("MSFT", "run-failed", "graph_wiring_failed"),)
    assert "failed latest runs: 1" in report.blockers


def test_quality_report_passes_when_latest_runs_are_grounded(tmp_path: Path) -> None:
    conn = connect(tmp_path / "noesis.db")
    try:
        migrate(conn)
        seed_completed_run(conn)
        with with_tx(conn):
            conn.execute("DELETE FROM node_traces WHERE status = 'degraded'")

        report = build_quality_report(conn)

        assert report.status == "passed"
        assert report.warnings == ()
    finally:
        conn.close()


def test_quality_report_blocks_completed_data_gaps_and_warns_pending_gaps(
    tmp_path: Path,
) -> None:
    conn = connect(tmp_path / "noesis.db")
    try:
        migrate(conn)
        seed_completed_run(conn)
        with with_tx(conn):
            conn.execute("DELETE FROM node_traces WHERE status = 'degraded'")
            _insert_position(conn, "position-msft", "MSFT", "Microsoft")
            _insert_run(conn, "run-msft", "position-msft", "completed")
            _insert_position(conn, "position-sony", "SONY", "Sony Group")
            _insert_run(conn, "run-sony", "position-sony", "awaiting_confirmation")

        report = build_quality_report(conn)

        assert report.status == "blocked"
        assert report.completed_runs_without_evidence == ("run-msft",)
        assert report.completed_runs_without_thesis == ("run-msft",)
        assert report.pending_runs_without_evidence == ("run-sony",)
        assert report.pending_runs_without_thesis == ("run-sony",)
        assert "completed runs without evidence: 1" in report.blockers
        assert "completed runs without thesis: 1" in report.blockers
        assert "pending runs without evidence: 1" in report.warnings
        assert "pending runs without thesis: 1" in report.warnings
    finally:
        conn.close()


def test_quality_markdown_and_json_formats_include_warning_details(
    tmp_path: Path,
) -> None:
    conn = _seed_quality_db(tmp_path)
    try:
        report = build_quality_report(conn)
    finally:
        conn.close()

    markdown = format_quality_report(report, output_format="markdown")
    json_text = format_quality_report(report, output_format="json")

    assert "# Noesis data quality report" in markdown
    assert "| total_positions | 2 |" in markdown
    assert "## Blockers" in markdown
    assert "- failed latest runs: 1" in markdown
    assert '"status": "blocked"' in json_text
    assert '"graph_wiring_failed"' in json_text


def _seed_quality_db(tmp_path: Path) -> sqlite3.Connection:
    conn = connect(tmp_path / "noesis.db")
    migrate(conn)
    seed_completed_run(conn)
    with with_tx(conn):
        conn.execute(
            """
            INSERT INTO positions(
              id, user_id, symbol, market, name, kind, qty, cost_basis,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "position-msft",
                "local-user",
                "MSFT",
                "US",
                "Microsoft",
                "owned",
                None,
                None,
                NOW,
                NOW,
            ),
        )
        conn.execute(
            """
            INSERT INTO run_registry(
              id, position_id, entity_id, node_kind, status, started_at,
              ended_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "run-failed",
                "position-msft",
                None,
                "seed",
                "failed",
                NOW,
                NOW,
                NOW,
            ),
        )
        conn.execute(
            """
            INSERT INTO node_traces(
              id, run_id, node_name, entity_id, inputs_ref, outputs_ref, status,
              reason, fallback_used, model_id, evidence_ids_json, started_at,
              ended_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "trace-failed",
                "run-failed",
                "finalize",
                None,
                "state",
                "failed",
                "failed",
                "graph_wiring_failed",
                None,
                None,
                None,
                NOW,
                NOW,
                NOW,
            ),
        )
    return conn


def _insert_position(
    conn: sqlite3.Connection,
    position_id: str,
    symbol: str,
    name: str,
) -> None:
    conn.execute(
        """
        INSERT INTO positions(
          id, user_id, symbol, market, name, kind, qty, cost_basis,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            position_id,
            "local-user",
            symbol,
            "US",
            name,
            "owned",
            None,
            None,
            NOW,
            NOW,
        ),
    )


def _insert_run(
    conn: sqlite3.Connection,
    run_id: str,
    position_id: str,
    status: str,
) -> None:
    conn.execute(
        """
        INSERT INTO run_registry(
          id, position_id, entity_id, node_kind, status, started_at,
          ended_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            position_id,
            None,
            "seed",
            status,
            NOW,
            NOW,
            NOW,
        ),
    )
