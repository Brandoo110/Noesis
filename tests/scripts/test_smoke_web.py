import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def test_smoke_web_parse_args_defaults() -> None:
    module = _load_smoke_module()

    args = module.parse_args(())

    assert args.api == "http://127.0.0.1:8000"
    assert args.web == "http://127.0.0.1:5173"
    assert args.timeout == 5.0


def test_smoke_web_parse_args_overrides_urls() -> None:
    module = _load_smoke_module()

    args = module.parse_args(("--api", "http://api.local/", "--web", "http://web.local/"))

    assert args.api == "http://api.local"
    assert args.web == "http://web.local"


def test_smoke_web_help_runs_as_script() -> None:
    root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "scripts/smoke_web.py", "--help"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "--api" in result.stdout
    assert "--web" in result.stdout


def test_smoke_web_success_path_checks_core_surfaces() -> None:
    module = _load_smoke_module()
    client = FakeClient(
        {
            "http://web.local": FakeResponse(200, text="<title>Noesis</title>"),
            "http://api.local/positions": FakeResponse(
                200,
                [
                    {
                        "id": "position-1",
                        "symbol": "AAPL",
                        "latest_run_id": "run-1",
                        "latest_run_entity": {"id": "entity-aapl"},
                    }
                ],
            ),
            "http://api.local/portfolio/brief": FakeResponse(
                200,
                {
                    "positions": [{"symbol": "AAPL"}],
                    "overlaps": [],
                    "run_health": {"total_latest_runs": 1},
                },
            ),
            "http://api.local/portfolio/overlaps": FakeResponse(200, []),
            "http://api.local/runs/run-1": FakeResponse(
                200,
                {
                    "run_id": "run-1",
                    "status": "completed",
                    "evidences": [{"id": "evidence-1"}],
                    "thesis": {"id": "thesis-1"},
                },
            ),
            "http://api.local/entities/entity-aapl/neighbors": FakeResponse(
                200,
                {"entity_id": "entity-aapl", "edges": []},
            ),
            "http://api.local/evidences/evidence-1": FakeResponse(
                200,
                {"id": "evidence-1"},
            ),
        }
    )

    checks = module.run_smoke(
        client,
        module.WebSmokeArgs(
            api="http://api.local",
            web="http://web.local",
            timeout=5.0,
        ),
    )

    assert {check.name for check in checks} == {
        "web_home",
        "positions",
        "portfolio_brief",
        "portfolio_overlaps",
        "latest_run",
        "neighbors",
        "evidence_detail",
    }
    assert all(check.status == "passed" for check in checks)
    assert "http://api.local/runs/run-1" in client.requested


def test_smoke_web_reports_failures_without_crashing() -> None:
    module = _load_smoke_module()
    client = FakeClient(
        {
            "http://web.local": FakeResponse(200, text="<title>Noesis</title>"),
            "http://api.local/positions": FakeResponse(500, {"error": "down"}),
            "http://api.local/portfolio/brief": FakeResponse(
                200,
                {
                    "positions": [],
                    "overlaps": [],
                    "run_health": {"total_latest_runs": 0},
                },
            ),
            "http://api.local/portfolio/overlaps": FakeResponse(200, []),
        }
    )

    checks = module.run_smoke(
        client,
        module.WebSmokeArgs(
            api="http://api.local",
            web="http://web.local",
            timeout=5.0,
        ),
    )

    assert any(
        check.name == "positions" and check.status == "failed" and "status=500" in check.detail
        for check in checks
    )
    assert any(check.name == "latest_run" and check.status == "skipped" for check in checks)


def _load_smoke_module() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "smoke_web.py"
    spec = importlib.util.spec_from_file_location("smoke_web", path)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load smoke_web.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["smoke_web"] = module
    spec.loader.exec_module(module)
    return module


class FakeClient:
    def __init__(self, responses: dict[str, "FakeResponse"]) -> None:
        self._responses = responses
        self.requested: list[str] = []

    def get(self, url: str) -> "FakeResponse":
        self.requested.append(url)
        if url not in self._responses:
            raise AssertionError(f"unexpected URL: {url}")
        return self._responses[url]


class FakeResponse:
    def __init__(self, status_code: int, payload: Any = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> Any:
        return self._payload
