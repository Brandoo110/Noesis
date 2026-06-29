import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Sequence


def test_smoke_release_parse_args_defaults() -> None:
    module = _load_release_module()

    args = module.parse_args(())

    assert args.api == "http://127.0.0.1:8000"
    assert args.web == "http://127.0.0.1:5173"
    assert args.out_root == Path("output/release-smoke")
    assert args.timeout == 120.0
    assert args.symbol == "AAPL"
    assert args.run_id is None


def test_smoke_release_help_runs_as_script() -> None:
    root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "scripts/smoke_release.py", "--help"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "--api" in result.stdout
    assert "--web" in result.stdout
    assert "--out-root" in result.stdout


def test_smoke_release_writes_manifest_summary_and_command_logs(tmp_path: Path) -> None:
    module = _load_release_module()
    runner = FakeRunner()
    args = module.ReleaseArgs(
        api="http://api.local",
        web="http://web.local",
        out_root=tmp_path / "release-smoke",
        timeout=5.0,
        symbol="MSFT",
        run_id="test-run",
        skip_live=False,
    )

    result = module.run_release_smoke(args, runner=runner)

    package = tmp_path / "release-smoke" / "test-run"
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    summary = (package / "summary.md").read_text(encoding="utf-8")

    assert result.status == "passed"
    assert len(result.runs) == 5
    assert manifest["status"] == "passed"
    assert manifest["api"] == "http://api.local"
    assert manifest["web"] == "http://web.local"
    assert {run["name"] for run in manifest["runs"]} == {
        "web_api",
        "quality_report",
        "visual",
        "ui_flow",
        "ui_mutation",
    }
    assert "| web_api | passed | 0 |" in summary
    assert "| quality_report | passed | 0 |" in summary
    assert "| ui_mutation | passed | 0 |" in summary
    assert (package / "web_api" / "stdout.txt").exists()
    assert (package / "quality_report" / "stdout.txt").exists()
    assert (package / "visual" / "stdout.txt").exists()
    assert (package / "ui_flow" / "stdout.txt").exists()
    assert (package / "ui_mutation" / "stdout.txt").exists()
    assert any("scripts/smoke_web.py" in command for command in runner.commands[0])
    assert any("scripts/quality_report.py" in command for command in runner.commands[1])
    assert any("scripts/smoke_visual.py" in command for command in runner.commands[2])


def test_smoke_release_can_skip_live_commands(tmp_path: Path) -> None:
    module = _load_release_module()
    runner = FakeRunner()
    args = module.ReleaseArgs(
        api="http://api.local",
        web="http://web.local",
        out_root=tmp_path / "release-smoke",
        timeout=5.0,
        symbol="MSFT",
        run_id="test-run",
        skip_live=True,
    )

    result = module.run_release_smoke(args, runner=runner)

    assert result.status == "passed"
    assert [run.name for run in result.runs] == ["ui_mutation"]
    assert len(runner.commands) == 1


def _load_release_module() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "smoke_release.py"
    spec = importlib.util.spec_from_file_location("smoke_release", path)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load smoke_release.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["smoke_release"] = module
    spec.loader.exec_module(module)
    return module


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[Sequence[str]] = []

    def __call__(self, command: Sequence[str], timeout: float) -> object:
        self.commands.append(command)
        return FakeCompletedCommand(
            returncode=0,
            stdout=f"[PASSED] {' '.join(command)}",
            stderr="",
        )


class FakeCompletedCommand:
    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
