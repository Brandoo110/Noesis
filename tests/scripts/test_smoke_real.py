import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def test_smoke_real_parse_args_defaults() -> None:
    module = _load_smoke_module()

    args = module.parse_args(())

    assert args.symbol == "AAPL"
    assert args.market == "US"


def test_smoke_real_parse_args_overrides_symbol_and_market() -> None:
    module = _load_smoke_module()

    args = module.parse_args(("--symbol", "TSLA", "--market", "US"))

    assert args.symbol == "TSLA"
    assert args.market == "US"


def test_smoke_real_docstring_names_required_keys_and_command() -> None:
    module = _load_smoke_module()

    assert module.__doc__ is not None
    assert "DEEPSEEK" in module.__doc__
    assert "LIGHT" in module.__doc__
    assert "RISK" in module.__doc__
    assert "TAVILY" in module.__doc__
    assert "python scripts/smoke_real.py --symbol AAPL --market US" in module.__doc__


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


def _load_smoke_module() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "smoke_real.py"
    spec = importlib.util.spec_from_file_location("smoke_real", path)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load smoke_real.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["smoke_real"] = module
    spec.loader.exec_module(module)
    return module
