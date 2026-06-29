#!/usr/bin/env python3
"""Run an isolated mutating UI smoke for Noesis.

The script starts a fixture FastAPI backend and a Vite dev server against a
temporary SQLite database, then uses a real browser to create a holding, start
research, open the graph, and verify the persisted API state.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp
from typing import Any, Literal

import httpx

try:
    from scripts.process_smoke import (
        free_port,
        start_fixture_api,
        start_vite_web,
        stop_process,
        wait_for_json,
        wait_for_text,
    )
except ModuleNotFoundError:
    from process_smoke import (
        free_port,
        start_fixture_api,
        start_vite_web,
        stop_process,
        wait_for_json,
        wait_for_text,
    )

CheckStatus = Literal["passed", "failed"]
CommandRunner = Callable[[Sequence[str], float], str]


@dataclass(frozen=True)
class MutationSmokeArgs:
    web_port: int
    api_port: int
    out_dir: Path
    timeout: float
    symbol: str
    market: str
    name: str
    pwcli: str
    session: str
    keep_tmp: bool


@dataclass(frozen=True)
class MutationFlowArgs:
    web: str
    out_dir: Path
    timeout: float
    symbol: str
    market: str
    name: str
    pwcli: str
    session: str


@dataclass(frozen=True)
class MutationCheck:
    name: str
    status: CheckStatus
    detail: str


def parse_args(argv: Iterable[str] | None = None) -> MutationSmokeArgs:
    parser = argparse.ArgumentParser(description="Run isolated Noesis mutating UI smoke")
    parser.add_argument("--web-port", type=int, default=0)
    parser.add_argument("--api-port", type=int, default=0)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("output/playwright/ui-mutation"),
    )
    parser.add_argument("--timeout", type=float, default=75.0)
    parser.add_argument("--symbol", default="NOEUI")
    parser.add_argument("--market", default="US")
    parser.add_argument("--name", default="Noesis UI Fixture")
    parser.add_argument("--pwcli", default=_default_pwcli())
    parser.add_argument("--session", default="noesis-ui-mutation")
    parser.add_argument("--keep-tmp", action="store_true")
    parsed = parser.parse_args(tuple(argv) if argv is not None else None)
    return MutationSmokeArgs(
        web_port=parsed.web_port,
        api_port=parsed.api_port,
        out_dir=parsed.out_dir,
        timeout=parsed.timeout,
        symbol=parsed.symbol.upper(),
        market=parsed.market,
        name=parsed.name,
        pwcli=parsed.pwcli,
        session=parsed.session,
        keep_tmp=parsed.keep_tmp,
    )


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.keep_tmp:
        tmp_path = Path(mkdtemp(prefix="noesis-ui-mutation-"))
        checks = run_isolated_mutation(args, tmp_path)
        checks.append(MutationCheck("tmp_dir", "passed", str(tmp_path)))
    else:
        with TemporaryDirectory(prefix="noesis-ui-mutation-") as tmp_dir:
            checks = run_isolated_mutation(args, Path(tmp_dir))
    for check in checks:
        print(f"[{check.status.upper()}] {check.name}: {check.detail}")
    return 0 if all(check.status == "passed" for check in checks) else 1


def run_isolated_mutation(
    args: MutationSmokeArgs,
    tmp_path: Path,
) -> list[MutationCheck]:
    api_port = args.api_port or free_port()
    web_port = args.web_port or free_port()
    api = f"http://127.0.0.1:{api_port}"
    web = f"http://127.0.0.1:{web_port}"
    checks: list[MutationCheck] = []
    api_proc: subprocess.Popen[str] | None = None
    web_proc: subprocess.Popen[str] | None = None
    api_log = (args.out_dir / "fixture-api.log").open("w", encoding="utf-8")
    web_log = (args.out_dir / "fixture-web.log").open("w", encoding="utf-8")
    try:
        api_proc = start_fixture_api(tmp_path, api_port, api_log)
        wait_for_json(f"{api}/positions", args.timeout)
        checks.append(MutationCheck("fixture_api", "passed", api))
        web_proc = start_vite_web(api, web_port, web_log)
        wait_for_text(web, "Noesis", args.timeout)
        checks.append(MutationCheck("fixture_web", "passed", web))
        checks.extend(
            run_mutation_flow(
                MutationFlowArgs(
                    web=web,
                    out_dir=args.out_dir,
                    timeout=args.timeout,
                    symbol=args.symbol,
                    market=args.market,
                    name=args.name,
                    pwcli=args.pwcli,
                    session=args.session,
                )
            )
        )
        checks.extend(_check_api_state(api, args.symbol, args.timeout))
    except Exception as exc:
        checks.append(MutationCheck("ui_mutation", "failed", str(exc)))
    finally:
        stop_process(web_proc)
        stop_process(api_proc)
        api_log.close()
        web_log.close()
    return checks


def run_mutation_flow(
    args: MutationFlowArgs, *, runner: CommandRunner | None = None
) -> list[MutationCheck]:
    command_runner = runner or _run_command
    args.out_dir.mkdir(parents=True, exist_ok=True)
    script_path = args.out_dir / "ui-mutation.js"
    screenshot_path = args.out_dir / "ui-mutation.png"
    script_path.write_text(_flow_script(args), encoding="utf-8")
    checks: list[MutationCheck] = []
    try:
        command_runner(_pw(args, "open", args.web), args.timeout)
        command_runner(_pw(args, "resize", "1280", "900"), args.timeout)
        snapshot = command_runner(_pw(args, "snapshot"), args.timeout)
        _require_text(snapshot, ("Noesis", "新增持仓", "持仓"))
        checks.append(MutationCheck("initial_snapshot", "passed", "workspace loaded"))
        command_runner(
            (*_pw(args, "run-code"), "--filename", str(script_path)),
            args.timeout,
        )
        checks.append(MutationCheck("write_flow", "passed", f"symbol={args.symbol}"))
        requests = command_runner(_pw(args, "requests"), args.timeout)
        _require_text(requests, ("POST", "/positions", "/runs"))
        checks.append(MutationCheck("network", "passed", "write API requests observed"))
        command_runner(
            (
                *_pw(args, "screenshot"),
                "--filename",
                str(screenshot_path),
                "--full-page",
            ),
            args.timeout,
        )
        checks.append(MutationCheck("screenshot", "passed", str(screenshot_path)))
    except Exception as exc:
        checks.append(MutationCheck("write_flow", "failed", str(exc)))
    _try_close(args, command_runner)
    return checks


def _flow_script(args: MutationFlowArgs) -> str:
    symbol = json.dumps(args.symbol)
    market = json.dumps(args.market)
    name = json.dumps(args.name)
    return f"""
async (page) => {{
  const symbol = {symbol};
  const market = {market};
  const name = {name};
  const expectText = async (text, timeout = 20000) => {{
    await page.getByText(text, {{ exact: false }}).first().waitFor({{ timeout }});
  }};
  await expectText('Noesis');
  await expectText('新增持仓');

  const form = page.getByRole('form', {{ name: '新增持仓表单' }});
  await form.getByLabel('Symbol').fill(symbol);
  await form.getByLabel('Market').fill(market);
  await form.getByLabel('Name').fill(name);
  await form.getByLabel('Kind').selectOption('owned');
  await form.getByRole('button', {{ name: '新增持仓' }}).click();

  await page.getByRole('list', {{ name: '持仓列表' }}).getByText(symbol).waitFor({{ timeout: 20000 }});
  await page.getByRole('button', {{ name: `开始研究 ${{symbol}}` }}).click();
  await page.getByLabel(`研究状态 ${{symbol}}`).waitFor({{ timeout: 30000 }});
  await page.getByRole('button', {{ name: `查看图谱 ${{symbol}}` }}).waitFor({{ timeout: 45000 }});
  await page.getByRole('button', {{ name: `查看图谱 ${{symbol}}` }}).click();
  await expectText(`研究图谱（以 ${{symbol}} 为种子）`, 30000);
  await page.getByRole('button', {{ name: `详情 ${{symbol}}` }}).click();
  await expectText('Stock detail / Thesis view', 30000);
  await expectText('证据', 30000);
}}
"""


def _check_api_state(api: str, symbol: str, timeout: float) -> list[MutationCheck]:
    deadline = time.monotonic() + timeout
    last_error = "state not checked"
    while time.monotonic() < deadline:
        try:
            positions = httpx.get(f"{api}/positions", timeout=5.0).json()
            position = _find_position(positions, symbol)
            if position is None:
                last_error = f"{symbol} position missing"
            elif not isinstance(position.get("latest_run_id"), str):
                last_error = "latest_run_id missing"
            else:
                run_id = str(position["latest_run_id"])
                detail = httpx.get(f"{api}/runs/{run_id}", timeout=5.0).json()
                if detail.get("status") not in {"awaiting_confirmation", "completed"}:
                    last_error = f"unexpected run status={detail.get('status')}"
                elif not detail.get("evidences"):
                    last_error = "run evidences missing"
                elif detail.get("thesis") is None:
                    last_error = "run thesis missing"
                else:
                    return [
                        MutationCheck("api_state", "passed", f"position={position['id']}"),
                        MutationCheck("run_detail", "passed", f"run_id={run_id}"),
                    ]
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.5)
    return [MutationCheck("api_state", "failed", last_error)]


def _find_position(payload: Any, symbol: str) -> dict[str, Any] | None:
    if not isinstance(payload, list):
        return None
    for item in payload:
        if isinstance(item, dict) and item.get("symbol") == symbol:
            return item
    return None


def _require_text(haystack: str, needles: tuple[str, ...]) -> None:
    missing = [needle for needle in needles if needle not in haystack]
    if missing:
        raise RuntimeError(f"missing text: {', '.join(missing)}")


def _run_command(command: Sequence[str], timeout: float) -> str:
    result = subprocess.run(
        list(command),
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{' '.join(command)} failed with {result.returncode}: {result.stderr or result.stdout}"
        )
    return result.stdout


def _pw(args: MutationFlowArgs, command: str, *values: str) -> tuple[str, ...]:
    return (args.pwcli, f"-s={args.session}", command, *values)


def _try_close(args: MutationFlowArgs, runner: CommandRunner) -> None:
    try:
        runner(_pw(args, "close"), args.timeout)
    except Exception:
        return


def _default_pwcli() -> str:
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    return os.environ.get(
        "PWCLI",
        str(codex_home / "skills" / "playwright" / "scripts" / "playwright_cli.sh"),
    )


if __name__ == "__main__":
    if shutil.which("npm") is None:
        raise SystemExit("npm is required to run the Vite fixture server")
    sys.exit(main())
