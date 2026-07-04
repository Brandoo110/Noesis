import json
import sqlite3
from pathlib import Path

from noesis.db.connection import connect
from noesis.db.migrate import migrate
from noesis.graph.runner import build_graph_deps
from noesis.tools.llm.fake import FakeLLMRouter
from noesis.tools.search.fake import FakeSearchAdapter
from tests.scripts.eval_fixture_helpers import load_eval_module, seed_completed_run

NOW = "2026-06-28T00:00:00Z"


def test_eval_parse_args_defaults_to_offline_from_db() -> None:
    module = load_eval_module()

    args = module.parse_args(())

    assert args.from_db is True
    assert args.format == "text"


def test_eval_parse_args_supports_live_json_format() -> None:
    module = load_eval_module()

    args = module.parse_args(("--live", "--format", "json"))

    assert args.from_db is False
    assert args.format == "json"


def test_eval_parse_args_supports_fixture_seeding() -> None:
    module = load_eval_module()

    args = module.parse_args(("--from-db", "--seed-fixtures"))

    assert args.from_db is True
    assert args.seed_fixtures is True


def test_eval_existing_runs_return_case_and_average_metrics(tmp_path: Path) -> None:
    module = load_eval_module()
    conn = connect(tmp_path / "noesis.db")
    checkpoint_conn = sqlite3.connect(tmp_path / "checkpoints.db", check_same_thread=False)
    try:
        migrate(conn)
        seed_completed_run(conn)
        deps = build_graph_deps(
            conn=conn,
            checkpoint_conn=checkpoint_conn,
            chroma_dir=str(tmp_path / "chroma"),
            search=FakeSearchAdapter([]),
            llm=FakeLLMRouter(),
            now=lambda: NOW,
        )

        report = module.evaluate_existing_runs(
            (module.EvalCase(symbol="AAPL", market="US", name="Apple Inc."),),
            deps,
        )

        assert len(report.results) == 1
        assert report.results[0].symbol == "AAPL"
        assert report.results[0].status == "evaluated"
        assert report.results[0].metrics["grounding_rate"] == 1.0
        assert report.results[0].trace_summary == {
            "total": 2,
            "started": 0,
            "success": 1,
            "degraded": 1,
            "failed": 0,
        }
        assert report.averages["grounding_rate"] == 1.0
        assert report.agentops.total_runs == 1
        assert "average grounding_rate=1.00" in module.format_report(report)
        assert "agentops total_runs=1" in module.format_report(report)
    finally:
        checkpoint_conn.close()
        conn.close()


def test_eval_json_report_includes_mode_cases_metrics_and_trace_summary(
    tmp_path: Path,
) -> None:
    report, module = _evaluated_report(tmp_path)

    payload = json.loads(
        module.format_report(report, mode="from_db", output_format="json")
    )

    assert payload["mode"] == "from_db"
    assert payload["averages"]["grounding_rate"] == 1.0
    assert payload["agentops"]["total_runs"] == 1
    assert payload["agentops"]["evidence_coverage"] == 1.0
    assert payload["cases"][0]["symbol"] == "AAPL"
    assert payload["cases"][0]["trace_summary"]["degraded"] == 1


def test_eval_markdown_report_labels_mode_and_trace_summary(tmp_path: Path) -> None:
    report, module = _evaluated_report(tmp_path)

    markdown = module.format_report(report, mode="from_db", output_format="markdown")

    assert "# Noesis eval report" in markdown
    assert "Mode: `from_db`" in markdown
    assert "## AgentOps" in markdown
    assert "- total_runs: 1" in markdown
    assert "| AAPL | evaluated | run-aapl | 1.00 | 1.00 | 1.00 | 1.00 | 2 / 1 / 0 |" in markdown


def test_eval_seed_fixtures_completes_all_eval_cases(tmp_path: Path) -> None:
    module = load_eval_module()
    conn = connect(tmp_path / "noesis.db")
    checkpoint_conn = sqlite3.connect(tmp_path / "checkpoints.db", check_same_thread=False)
    try:
        migrate(conn)
        deps = build_graph_deps(
            conn=conn,
            checkpoint_conn=checkpoint_conn,
            chroma_dir=str(tmp_path / "chroma"),
            search=FakeSearchAdapter([]),
            llm=FakeLLMRouter(),
            now=lambda: NOW,
        )

        module.seed_eval_fixture_runs(module.EVAL_CASES, deps)
        report = module.evaluate_existing_runs(module.EVAL_CASES, deps)

        assert len(report.results) >= 20
        assert {result.status for result in report.results} == {"evaluated"}
        assert report.agentops.total_runs >= 20
        assert report.agentops.evidence_coverage == 1.0
        source_document_count = conn.execute(
            "SELECT count(*) FROM source_documents"
        ).fetchone()[0]
        assert source_document_count >= 20
        conn.execute("DELETE FROM source_documents")
        conn.commit()
        module.seed_eval_fixture_runs(module.EVAL_CASES, deps)
        backfilled_count = conn.execute(
            "SELECT count(*) FROM source_documents"
        ).fetchone()[0]
        assert backfilled_count >= 20
    finally:
        checkpoint_conn.close()
        conn.close()


def test_eval_live_positions_use_eval_user_without_touching_local_user(
    tmp_path: Path,
) -> None:
    module = load_eval_module()
    conn = connect(tmp_path / "noesis.db")
    checkpoint_conn = sqlite3.connect(tmp_path / "checkpoints.db", check_same_thread=False)
    try:
        migrate(conn)
        seed_completed_run(conn)
        deps = build_graph_deps(
            conn=conn,
            checkpoint_conn=checkpoint_conn,
            chroma_dir=str(tmp_path / "chroma"),
            search=FakeSearchAdapter([]),
            llm=FakeLLMRouter(),
            now=lambda: NOW,
        )
        before_count = _position_count(conn, "local-user")

        position_id = module._ensure_position(
            module.EvalCase(symbol="AAPL", market="US", name="Apple Inc."),
            deps,
        )

        assert position_id != "position-aapl"
        assert _position_count(conn, "local-user") == before_count
        assert _position_count(conn, "eval-user") == 1
    finally:
        checkpoint_conn.close()
        conn.close()


def test_eval_fixture_seeding_uses_eval_user_without_touching_local_user(
    tmp_path: Path,
) -> None:
    module = load_eval_module()
    conn = connect(tmp_path / "noesis.db")
    checkpoint_conn = sqlite3.connect(tmp_path / "checkpoints.db", check_same_thread=False)
    try:
        migrate(conn)
        seed_completed_run(conn)
        deps = build_graph_deps(
            conn=conn,
            checkpoint_conn=checkpoint_conn,
            chroma_dir=str(tmp_path / "chroma"),
            search=FakeSearchAdapter([]),
            llm=FakeLLMRouter(),
            now=lambda: NOW,
        )
        before_count = _position_count(conn, "local-user")

        module.seed_eval_fixture_runs(module.EVAL_CASES, deps)

        assert _position_count(conn, "local-user") == before_count
        assert _position_count(conn, "eval-user") >= 20
    finally:
        checkpoint_conn.close()
        conn.close()


def _evaluated_report(tmp_path: Path) -> tuple[object, object]:
    module = load_eval_module()
    conn = connect(tmp_path / "noesis.db")
    checkpoint_conn = sqlite3.connect(tmp_path / "checkpoints.db", check_same_thread=False)
    try:
        migrate(conn)
        seed_completed_run(conn)
        deps = build_graph_deps(
            conn=conn,
            checkpoint_conn=checkpoint_conn,
            chroma_dir=str(tmp_path / "chroma"),
            search=FakeSearchAdapter([]),
            llm=FakeLLMRouter(),
            now=lambda: NOW,
        )
        report = module.evaluate_existing_runs(
            (module.EvalCase(symbol="AAPL", market="US", name="Apple Inc."),),
            deps,
        )
        return report, module
    finally:
        checkpoint_conn.close()
        conn.close()


def _position_count(conn: sqlite3.Connection, user_id: str) -> int:
    return int(
        conn.execute(
            "SELECT count(*) FROM positions WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
    )
