import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Sequence


def test_smoke_ui_mutation_parse_args_defaults() -> None:
    module = _load_mutation_module()

    args = module.parse_args(())

    assert args.web_port == 0
    assert args.api_port == 0
    assert args.out_dir == Path("output/playwright/ui-mutation")
    assert args.timeout == 75.0
    assert args.symbol == "NOEUI"
    assert args.market == "US"
    assert args.name == "Noesis UI Fixture"
    assert args.session == "noesis-ui-mutation"


def test_smoke_ui_mutation_help_runs_as_script() -> None:
    root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "scripts/smoke_ui_mutation.py", "--help"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "--symbol" in result.stdout
    assert "--api-port" in result.stdout
    assert "--web-port" in result.stdout


def test_smoke_ui_mutation_runs_write_flow_commands(tmp_path: Path) -> None:
    module = _load_mutation_module()
    runner = FakeRunner()

    checks = module.run_mutation_flow(
        module.MutationFlowArgs(
            web="http://web.local",
            out_dir=tmp_path / "out",
            timeout=5.0,
            symbol="NOEUI",
            market="US",
            name="Noesis UI Fixture",
            pwcli="/tmp/playwright_cli.sh",
            session="test-ui-mutation",
        ),
        runner=runner,
    )

    assert all(check.status == "passed" for check in checks)
    assert _action(runner.commands[0]) == "open"
    assert any(_action(command) == "snapshot" for command in runner.commands)
    assert any(_action(command) == "run-code" for command in runner.commands)
    assert any(_action(command) == "requests" for command in runner.commands)
    script = (tmp_path / "out" / "ui-mutation.js").read_text(encoding="utf-8")
    assert "新增持仓表单" in script
    assert "开始研究 ${symbol}" in script
    assert "个股详情" in script
    assert "graphScreenshot" in script
    assert "state: 'hidden'" in script
    assert (tmp_path / "out" / "ui-mutation.js").exists()


def _load_mutation_module() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "smoke_ui_mutation.py"
    spec = importlib.util.spec_from_file_location("smoke_ui_mutation", path)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load smoke_ui_mutation.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["smoke_ui_mutation"] = module
    spec.loader.exec_module(module)
    return module


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[Sequence[str]] = []

    def __call__(self, command: Sequence[str], timeout: float) -> str:
        self.commands.append(command)
        action = _action(command)
        if action == "snapshot":
            return "组合工作台\n添加持仓\n持仓\n"
        if action == "requests":
            return "\n".join(
                [
                    "GET http://web.local/positions 200",
                    "POST http://web.local/positions 201",
                    "POST http://web.local/runs 200",
                    "GET http://web.local/runs/run-1 200",
                ]
            )
        return ""


def _action(command: Sequence[str]) -> str:
    return command[2] if len(command) > 2 and command[1].startswith("-s=") else command[1]
