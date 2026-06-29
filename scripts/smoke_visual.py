#!/usr/bin/env python3
"""Visual smoke and baseline check for the Noesis web workspace.

Usage:
python scripts/smoke_visual.py --web http://127.0.0.1:5173 --update-baseline
python scripts/smoke_visual.py --web http://127.0.0.1:5173
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Literal, Sequence

try:
    from scripts.png_checks import PngStats, diff_ratio, is_nonblank, png_stats
except ModuleNotFoundError:
    from png_checks import PngStats, diff_ratio, is_nonblank, png_stats

REQUIRED_TEXT = ("Noesis", "组合 Brief", "Brief 运行健康", "持仓")

CheckStatus = Literal["passed", "failed"]
CommandRunner = Callable[[Sequence[str], float], str]


@dataclass(frozen=True)
class VisualSmokeArgs:
    web: str
    out_dir: Path
    baseline_dir: Path
    timeout: float
    update_baseline: bool
    max_diff_ratio: float
    pixel_tolerance: int
    min_unique_colors: int
    pwcli: str
    session: str


@dataclass(frozen=True)
class Viewport:
    name: str
    width: int
    height: int


@dataclass(frozen=True)
class VisualCheck:
    name: str
    status: CheckStatus
    detail: str


VIEWPORTS = (
    Viewport(name="desktop", width=1280, height=900),
    Viewport(name="mobile", width=390, height=844),
)


def parse_args(argv: Iterable[str] | None = None) -> VisualSmokeArgs:
    parser = argparse.ArgumentParser(description="Run Noesis visual smoke checks")
    parser.add_argument("--web", default="http://127.0.0.1:5173")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("output/playwright/visual-smoke"),
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=Path("web/visual-baselines"),
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--max-diff-ratio", type=float, default=0.015)
    parser.add_argument("--pixel-tolerance", type=int, default=12)
    parser.add_argument("--min-unique-colors", type=int, default=16)
    parser.add_argument("--pwcli", default=_default_pwcli())
    parser.add_argument("--session", default="noesis-visual")
    parsed = parser.parse_args(tuple(argv) if argv is not None else None)
    return VisualSmokeArgs(
        web=parsed.web.rstrip("/"),
        out_dir=parsed.out_dir,
        baseline_dir=parsed.baseline_dir,
        timeout=parsed.timeout,
        update_baseline=parsed.update_baseline,
        max_diff_ratio=parsed.max_diff_ratio,
        pixel_tolerance=parsed.pixel_tolerance,
        min_unique_colors=parsed.min_unique_colors,
        pwcli=parsed.pwcli,
        session=parsed.session,
    )


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    checks = run_visual_smoke(args)
    for check in checks:
        print(f"[{check.status.upper()}] {check.name}: {check.detail}")
    return 0 if all(check.status == "passed" for check in checks) else 1


def run_visual_smoke(
    args: VisualSmokeArgs, *, runner: CommandRunner | None = None
) -> list[VisualCheck]:
    command_runner = runner or _run_command
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.baseline_dir.mkdir(parents=True, exist_ok=True)
    checks: list[VisualCheck] = []
    manifest: dict[str, object] = {
        "web": args.web,
        "viewports": [],
    }
    for viewport in VIEWPORTS:
        screenshot = args.out_dir / f"{viewport.name}.png"
        baseline = args.baseline_dir / f"{viewport.name}.png"
        checks.extend(
            _capture_viewport(args, viewport, screenshot, runner=command_runner)
        )
        if any(check.status == "failed" for check in checks if check.name.startswith(viewport.name)):
            continue
        stats = png_stats(screenshot)
        checks.append(_nonblank_check(viewport, stats, args.min_unique_colors))
        if args.update_baseline:
            shutil.copyfile(screenshot, baseline)
            checks.append(
                VisualCheck(
                    f"{viewport.name}_baseline",
                    "passed",
                    f"updated {baseline}",
                )
            )
        else:
            checks.append(
                _baseline_check(
                    viewport,
                    screenshot,
                    baseline,
                    args.max_diff_ratio,
                    args.pixel_tolerance,
                )
            )
        manifest["viewports"].append(
            {
                "name": viewport.name,
                "width": viewport.width,
                "height": viewport.height,
                "screenshot": str(screenshot),
                "baseline": str(baseline),
                "sha256": stats.digest,
            }
        )
    _try_close(args, command_runner)
    if args.update_baseline:
        (args.baseline_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return checks


def _capture_viewport(
    args: VisualSmokeArgs,
    viewport: Viewport,
    screenshot: Path,
    *,
    runner: CommandRunner,
) -> list[VisualCheck]:
    checks: list[VisualCheck] = []
    prefix = viewport.name
    try:
        runner(_pw(args, "open", args.web), args.timeout)
        runner(_pw(args, "resize", str(viewport.width), str(viewport.height)), args.timeout)
        snapshot = runner(_pw(args, "snapshot"), args.timeout)
    except Exception as exc:
        return [VisualCheck(f"{prefix}_snapshot", "failed", str(exc))]
    missing = [text for text in REQUIRED_TEXT if text not in snapshot]
    if missing:
        checks.append(
            VisualCheck(
                f"{prefix}_snapshot",
                "failed",
                f"missing text: {', '.join(missing)}",
            )
        )
    else:
        checks.append(
            VisualCheck(
                f"{prefix}_snapshot",
                "passed",
                f"{viewport.width}x{viewport.height} required text present",
            )
        )
    try:
        runner(
            (
                *_pw(args, "screenshot"),
                "--filename",
                str(screenshot),
                "--full-page",
            ),
            args.timeout,
        )
    except Exception as exc:
        checks.append(VisualCheck(f"{prefix}_screenshot", "failed", str(exc)))
    else:
        checks.append(
            VisualCheck(
                f"{prefix}_screenshot",
                "passed",
                str(screenshot),
            )
        )
    return checks


def _nonblank_check(
    viewport: Viewport, stats: PngStats, min_unique_colors: int
) -> VisualCheck:
    if not is_nonblank(stats, min_unique_colors=min_unique_colors):
        return VisualCheck(
            f"{viewport.name}_nonblank",
            "failed",
            f"{stats.width}x{stats.height} unique_colors={stats.unique_colors}",
        )
    return VisualCheck(
        f"{viewport.name}_nonblank",
        "passed",
        f"{stats.width}x{stats.height} unique_colors={stats.unique_colors}",
    )


def _baseline_check(
    viewport: Viewport,
    current_path: Path,
    baseline_path: Path,
    max_diff_ratio: float,
    tolerance: int,
) -> VisualCheck:
    if not baseline_path.exists():
        return VisualCheck(
            f"{viewport.name}_baseline",
            "failed",
            f"missing baseline {baseline_path}; rerun with --update-baseline",
        )
    current = png_stats(current_path)
    baseline = png_stats(baseline_path)
    ratio = diff_ratio(current, baseline, tolerance=tolerance)
    if ratio > max_diff_ratio:
        return VisualCheck(
            f"{viewport.name}_baseline",
            "failed",
            f"diff_ratio={ratio:.4f} max={max_diff_ratio:.4f}",
        )
    return VisualCheck(
        f"{viewport.name}_baseline",
        "passed",
        f"diff_ratio={ratio:.4f} max={max_diff_ratio:.4f}",
    )


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


def _pw(args: VisualSmokeArgs, command: str, *values: str) -> tuple[str, ...]:
    return (args.pwcli, f"-s={args.session}", command, *values)


def _try_close(args: VisualSmokeArgs, runner: CommandRunner) -> None:
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
