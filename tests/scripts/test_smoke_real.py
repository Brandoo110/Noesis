import importlib.util
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

import pytest

from noesis.db.connection import connect
from noesis.db.migrate import migrate
from noesis.graph.runner import build_graph_deps
from noesis.graph.schemas import IngestedDoc
from noesis.tools.search.fake import FakeSearchAdapter
from tests.api.conftest import ApiFakeLLM, NOW


def test_smoke_real_parse_args_defaults() -> None:
    module = _load_smoke_module()

    args = module.parse_args(())

    assert args.symbol == "AAPL"
    assert args.market == "US"
    assert args.expand is False


def test_smoke_real_parse_args_overrides_symbol_and_market() -> None:
    module = _load_smoke_module()

    args = module.parse_args(("--symbol", "TSLA", "--market", "US", "--expand"))

    assert args.symbol == "TSLA"
    assert args.market == "US"
    assert args.expand is True


def test_smoke_real_docstring_names_required_keys_and_command() -> None:
    module = _load_smoke_module()

    assert module.__doc__ is not None
    assert "DEEPSEEK" in module.__doc__
    assert "LIGHT" in module.__doc__
    assert "RISK" in module.__doc__
    assert "TAVILY" in module.__doc__
    assert "python scripts/smoke_real.py --symbol AAPL --market US --expand" in module.__doc__


def test_smoke_real_help_runs_as_script() -> None:
    root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "scripts/smoke_real.py", "--help"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "--symbol" in result.stdout
    assert "--expand" in result.stdout


def test_smoke_real_expand_branch_uses_fake_runtime(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_smoke_module()
    monkeypatch.setattr(module, "Settings", lambda: object())
    monkeypatch.setattr(module, "_runtime", _fake_runtime(module))

    result = module.main(("--symbol", "AAPL", "--market", "US", "--expand"))
    output = capsys.readouterr().out

    assert result == 0
    assert "graph_edges: 1" in output
    assert "relation=supplier" in output
    assert "basis=source_backed" in output
    assert "to_name=Taiwan Semiconductor Manufacturing" in output
    assert "to_symbol=TSM" in output
    assert "source_backed_has_evidence=True" in output
    assert "second_expand_status: cached" in output
    assert "expand_run_count_unchanged: True" in output


def _load_smoke_module() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "smoke_real.py"
    spec = importlib.util.spec_from_file_location("smoke_real", path)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load smoke_real.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["smoke_real"] = module
    spec.loader.exec_module(module)
    return module


def _fake_runtime(module: ModuleType) -> object:
    @contextmanager
    def runtime(settings: object, tmp_path: Path) -> Iterator[object]:
        conn = connect(tmp_path / "noesis.db")
        checkpoint_conn = sqlite3.connect(
            tmp_path / "checkpoints.db",
            check_same_thread=False,
        )
        try:
            migrate(conn)
            deps = build_graph_deps(
                conn=conn,
                checkpoint_conn=checkpoint_conn,
                chroma_dir=str(tmp_path / "chroma"),
                search=FakeSearchAdapter(
                    [
                        IngestedDoc(
                            source="web",
                            source_tier=2,
                            title="Supplier update",
                            url="https://example.com/supplier",
                            text="Supplier pressure eased for Apple.",
                        )
                    ]
                ),
                llm=ApiFakeLLM(),
                now=lambda: NOW,
            )
            yield module.SmokeRuntime(
                deps=deps,
                conn=conn,
                checkpoint_conn=checkpoint_conn,
            )
        finally:
            checkpoint_conn.close()
            conn.close()

    return runtime
