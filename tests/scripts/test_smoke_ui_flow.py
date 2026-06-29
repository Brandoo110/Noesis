import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Sequence


def test_smoke_ui_flow_parse_args_defaults() -> None:
    module = _load_ui_flow_module()

    args = module.parse_args(())

    assert args.web == "http://127.0.0.1:5173"
    assert args.out_dir == Path("output/playwright/ui-flow")
    assert args.timeout == 45.0
    assert args.symbol == "AAPL"
    assert args.session == "noesis-ui-flow"


def test_smoke_ui_flow_help_runs_as_script() -> None:
    root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "scripts/smoke_ui_flow.py", "--help"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "--symbol" in result.stdout
    assert "--web" in result.stdout


def test_smoke_ui_flow_runs_browser_commands(tmp_path: Path) -> None:
    module = _load_ui_flow_module()
    runner = FakeRunner()

    checks = module.run_ui_flow(
        module.UiFlowArgs(
            web="http://web.local",
            out_dir=tmp_path / "out",
            timeout=5.0,
            symbol="AAPL",
            pwcli="/tmp/playwright_cli.sh",
            session="test-ui-flow",
        ),
        runner=runner,
    )

    assert all(check.status == "passed" for check in checks)
    assert _action(runner.commands[0]) == "open"
    assert any(_action(command) == "snapshot" for command in runner.commands)
    assert any(_action(command) == "run-code" for command in runner.commands)
    assert any(_action(command) == "requests" for command in runner.commands)
    assert (tmp_path / "out" / "ui-flow.js").exists()


def _load_ui_flow_module() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "smoke_ui_flow.py"
    spec = importlib.util.spec_from_file_location("smoke_ui_flow", path)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load smoke_ui_flow.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["smoke_ui_flow"] = module
    spec.loader.exec_module(module)
    return module


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[Sequence[str]] = []

    def __call__(self, command: Sequence[str], timeout: float) -> str:
        self.commands.append(command)
        action = _action(command)
        if action == "snapshot":
            return "Noesis\n组合 Brief\nBrief 运行健康\n持仓\n"
        if action == "requests":
            return "\n".join(
                [
                    "GET http://web.local/positions 200",
                    "GET http://web.local/portfolio/brief 200",
                    "GET http://web.local/portfolio/overlaps 200",
                ]
            )
        return ""


def _action(command: Sequence[str]) -> str:
    return command[2] if len(command) > 2 and command[1].startswith("-s=") else command[1]
