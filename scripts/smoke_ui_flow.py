#!/usr/bin/env python3
"""Run a real browser UI flow smoke for Noesis.

This smoke is intentionally read-mostly: it does not create positions or start
new research. It exercises the controls a user expects in the researched
workspace: search, filters, status panel, graph opening, detail, evidence drawer,
report view, and markdown export feedback.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Literal, Sequence

CheckStatus = Literal["passed", "failed"]
CommandRunner = Callable[[Sequence[str], float], str]


@dataclass(frozen=True)
class UiFlowArgs:
    web: str
    out_dir: Path
    timeout: float
    symbol: str
    pwcli: str
    session: str


@dataclass(frozen=True)
class UiFlowCheck:
    name: str
    status: CheckStatus
    detail: str


def parse_args(argv: Iterable[str] | None = None) -> UiFlowArgs:
    parser = argparse.ArgumentParser(description="Run Noesis UI flow smoke")
    parser.add_argument("--web", default="http://127.0.0.1:5173")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("output/playwright/ui-flow"),
    )
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--pwcli", default=_default_pwcli())
    parser.add_argument("--session", default="noesis-ui-flow")
    parsed = parser.parse_args(tuple(argv) if argv is not None else None)
    return UiFlowArgs(
        web=parsed.web.rstrip("/"),
        out_dir=parsed.out_dir,
        timeout=parsed.timeout,
        symbol=parsed.symbol.upper(),
        pwcli=parsed.pwcli,
        session=parsed.session,
    )


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    checks = run_ui_flow(args)
    for check in checks:
        print(f"[{check.status.upper()}] {check.name}: {check.detail}")
    return 0 if all(check.status == "passed" for check in checks) else 1


def run_ui_flow(
    args: UiFlowArgs, *, runner: CommandRunner | None = None
) -> list[UiFlowCheck]:
    command_runner = runner or _run_command
    args.out_dir.mkdir(parents=True, exist_ok=True)
    script_path = args.out_dir / "ui-flow.js"
    screenshot_path = args.out_dir / "ui-flow.png"
    script_path.write_text(_flow_script(args.symbol), encoding="utf-8")
    checks: list[UiFlowCheck] = []
    try:
        command_runner(_pw(args, "open", args.web), args.timeout)
        command_runner(_pw(args, "resize", "1280", "900"), args.timeout)
        snapshot = command_runner(_pw(args, "snapshot"), args.timeout)
        _require_text(snapshot, ("Noesis", "组合 Brief", "Brief 运行健康", "持仓"))
        checks.append(UiFlowCheck("initial_snapshot", "passed", "workspace loaded"))
        command_runner(
            (*_pw(args, "run-code"), "--filename", str(script_path)),
            args.timeout,
        )
        checks.append(UiFlowCheck("ui_flow", "passed", f"symbol={args.symbol}"))
        requests = command_runner(_pw(args, "requests"), args.timeout)
        _require_text(
            requests,
            ("/positions", "/portfolio/brief", "/portfolio/overlaps"),
        )
        checks.append(UiFlowCheck("network", "passed", "core API requests observed"))
        command_runner(
            (
                *_pw(args, "screenshot"),
                "--filename",
                str(screenshot_path),
                "--full-page",
            ),
            args.timeout,
        )
        checks.append(UiFlowCheck("screenshot", "passed", str(screenshot_path)))
    except Exception as exc:
        checks.append(UiFlowCheck("ui_flow", "failed", str(exc)))
    _try_close(args, command_runner)
    return checks


def _flow_script(symbol: str) -> str:
    safe_symbol = symbol.replace("\\", "\\\\").replace("'", "\\'")
    return f"""
async (page) => {{
  const symbol = '{safe_symbol}';
  const expectText = async (text) => {{
    await page.getByText(text, {{ exact: false }}).first().waitFor({{ timeout: 15000 }});
  }};
  await expectText('Noesis');
  await expectText('组合 Brief');
  await expectText('Brief 运行健康');

  await page.getByLabel('全局搜索').fill(symbol);
  await page.getByRole('list', {{ name: '持仓列表' }}).getByText(symbol).first().waitFor({{ timeout: 15000 }});
  await page.getByLabel('全局搜索').fill('');

  await page.getByRole('button', {{ name: '筛选' }}).click();
  await expectText('筛选面板');
  await page.getByLabel('持仓类型筛选').selectOption('owned');
  await page.getByLabel('研究状态筛选').selectOption('researched');
  await page.getByRole('button', {{ name: '重置筛选' }}).click();

  await page.getByRole('button', {{ name: '产品状态' }}).click();
  await expectText('Launch readiness');
  await expectText('本地优先');

  await page.getByRole('button', {{ name: new RegExp(`查看图谱 ${{symbol}}`, 'i') }}).first().click();
  await expectText(`研究图谱（以 ${{symbol}} 为种子）`);
  await page.getByRole('button', {{ name: 'Fit View' }}).click();
  await page.getByLabel('图谱边筛选').selectOption('source_backed');
  await page.getByLabel('图谱边筛选').selectOption('all');

  await page.getByRole('button', {{ name: new RegExp(`详情 ${{symbol}}`, 'i') }}).click();
  await expectText('Stock detail / Thesis view');
  await expectText('分类情报流');

  await page.getByRole('button', {{ name: '查看证据' }}).first().click();
  await expectText('证据详情');
  await page.keyboard.press('Escape');

  await page.getByRole('button', {{ name: '查看报告' }}).click();
  await expectText('report snapshot');
  await page.getByRole('button', {{ name: '导出 Markdown' }}).last().click();
  await expectText('.md');

  await page.getByRole('button', {{ name: '导出 Markdown' }}).first().click();
  await expectText('portfolio-brief.md');
}}
"""


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


def _pw(args: UiFlowArgs, command: str, *values: str) -> tuple[str, ...]:
    return (args.pwcli, f"-s={args.session}", command, *values)


def _try_close(args: UiFlowArgs, runner: CommandRunner) -> None:
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
    sys.exit(main())
