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
        assert "average grounding_rate=1.00" in module.format_report(report)
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
    assert payload["cases"][0]["symbol"] == "AAPL"
    assert payload["cases"][0]["trace_summary"]["degraded"] == 1


def test_eval_markdown_report_labels_mode_and_trace_summary(tmp_path: Path) -> None:
    report, module = _evaluated_report(tmp_path)

    markdown = module.format_report(report, mode="from_db", output_format="markdown")

    assert "# Noesis eval report" in markdown
    assert "Mode: `from_db`" in markdown
    assert "| AAPL | evaluated | run-aapl | 1.00 | 1.00 | 1.00 | 1.00 | 2 / 1 / 0 |" in markdown


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
