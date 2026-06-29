import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from tests.scripts.eval_fixture_helpers import NOW
from tests.scripts.eval_fixture_helpers import seed_completed_run


def test_quality_report_parse_args_defaults() -> None:
    module = _load_quality_script()

    args = module.parse_args(())

    assert args.db_path is None
    assert args.format == "text"
    assert args.fail_on_blockers is False
    assert args.fail_on_warnings is False


def test_quality_report_help_runs_as_script() -> None:
    root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "scripts/quality_report.py", "--help"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "--db-path" in result.stdout
    assert "--fail-on-blockers" in result.stdout
    assert "--fail-on-warnings" in result.stdout


def test_quality_report_main_passes_for_grounded_fixture(tmp_path: Path, capsys) -> None:
    module = _load_quality_script()
    db_path = tmp_path / "noesis.db"
    conn = connect(db_path)
    try:
        migrate(conn)
        seed_completed_run(conn)
        conn.execute("DELETE FROM node_traces WHERE status = 'degraded'")
        conn.commit()
    finally:
        conn.close()

    code = module.main(("--db-path", str(db_path), "--format", "markdown"))
    output = capsys.readouterr().out

    assert code == 0
    assert "# Noesis data quality report" in output
    assert "status: `passed`" in output


def test_quality_report_fail_on_warnings_returns_nonzero(tmp_path: Path) -> None:
    module = _load_quality_script()
    db_path = tmp_path / "noesis.db"
    conn = connect(db_path)
    try:
        migrate(conn)
    finally:
        conn.close()

    code = module.main(("--db-path", str(db_path), "--fail-on-warnings"))

    assert code == 1


def test_quality_report_fail_on_blockers_returns_nonzero_for_completed_gap(
    tmp_path: Path,
) -> None:
    module = _load_quality_script()
    db_path = tmp_path / "noesis.db"
    conn = connect(db_path)
    try:
        migrate(conn)
        seed_completed_run(conn)
        with with_tx(conn):
            conn.execute("DELETE FROM node_traces WHERE status = 'degraded'")
            conn.execute("DELETE FROM theses")
    finally:
        conn.close()

    code = module.main(("--db-path", str(db_path), "--fail-on-blockers"))

    assert code == 1


def test_quality_report_fail_on_blockers_allows_warnings(tmp_path: Path) -> None:
    module = _load_quality_script()
    db_path = tmp_path / "noesis.db"
    conn = connect(db_path)
    try:
        migrate(conn)
        seed_completed_run(conn)
        with with_tx(conn):
            conn.execute("DELETE FROM node_traces WHERE status = 'degraded'")
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
                    "run-msft",
                    "position-msft",
                    None,
                    "seed",
                    "awaiting_confirmation",
                    NOW,
                    NOW,
                    NOW,
                ),
            )
    finally:
        conn.close()

    code = module.main(("--db-path", str(db_path), "--fail-on-blockers"))

    assert code == 0


def _load_quality_script() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "quality_report.py"
    spec = importlib.util.spec_from_file_location("quality_report", path)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load quality_report.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["quality_report"] = module
    spec.loader.exec_module(module)
    return module
