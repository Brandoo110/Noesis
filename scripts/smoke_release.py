#!/usr/bin/env python3
"""Run Noesis smoke checks and archive a release evidence package."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Literal, Protocol, Sequence

SmokeStatus = Literal["passed", "failed"]


class CompletedCommand(Protocol):
    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def __call__(self, command: Sequence[str], timeout: float) -> CompletedCommand:
        ...


@dataclass(frozen=True)
class ReleaseArgs:
    api: str
    web: str
    out_root: Path
    timeout: float
    symbol: str
    run_id: str | None
    skip_live: bool


@dataclass(frozen=True)
class SmokeCommand:
    name: str
    command: tuple[str, ...]
    work_dir: Path


@dataclass(frozen=True)
class SmokeRun:
    name: str
    status: SmokeStatus
    returncode: int
    duration_seconds: float
    stdout_path: Path
    stderr_path: Path
    command: tuple[str, ...]
    artifacts: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class ReleaseResult:
    run_id: str
    package_dir: Path
    status: SmokeStatus
    runs: tuple[SmokeRun, ...]


def parse_args(argv: Iterable[str] | None = None) -> ReleaseArgs:
    parser = argparse.ArgumentParser(description="Archive Noesis smoke evidence")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--web", default="http://127.0.0.1:5173")
    parser.add_argument("--out-root", type=Path, default=Path("output/release-smoke"))
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--run-id")
    parser.add_argument(
        "--skip-live",
        action="store_true",
        help="only run the self-contained fixture mutation smoke",
    )
    parsed = parser.parse_args(tuple(argv) if argv is not None else None)
    return ReleaseArgs(
        api=parsed.api.rstrip("/"),
        web=parsed.web.rstrip("/"),
        out_root=parsed.out_root,
        timeout=parsed.timeout,
        symbol=parsed.symbol.upper(),
        run_id=parsed.run_id,
        skip_live=parsed.skip_live,
    )


def main(argv: Iterable[str] | None = None) -> int:
    result = run_release_smoke(parse_args(argv))
    print(f"release_smoke_package: {result.package_dir}")
    for run in result.runs:
        print(
            f"[{run.status.upper()}] {run.name}: "
            f"returncode={run.returncode} duration={run.duration_seconds:.2f}s"
        )
    print(f"summary: {result.package_dir / 'summary.md'}")
    return 0 if result.status == "passed" else 1


def run_release_smoke(
    args: ReleaseArgs,
    *,
    runner: CommandRunner | None = None,
) -> ReleaseResult:
    run_id = args.run_id or _timestamp_run_id()
    package_dir = args.out_root / run_id
    package_dir.mkdir(parents=True, exist_ok=True)
    command_runner = runner or _run_command
    runs: list[SmokeRun] = []
    for command in build_smoke_commands(args, package_dir):
        runs.append(_run_one(command, package_dir, args.timeout, command_runner))
    status: SmokeStatus = "passed" if all(run.status == "passed" for run in runs) else "failed"
    result = ReleaseResult(
        run_id=run_id,
        package_dir=package_dir,
        status=status,
        runs=tuple(runs),
    )
    _write_manifest(args, result)
    _write_summary(args, result)
    return result


def build_smoke_commands(args: ReleaseArgs, package_dir: Path) -> tuple[SmokeCommand, ...]:
    root = Path(__file__).resolve().parents[1]
    commands: list[SmokeCommand] = []
    if not args.skip_live:
        commands.extend(
            [
                SmokeCommand(
                    name="web_api",
                    command=(
                        sys.executable,
                        "scripts/smoke_web.py",
                        "--api",
                        args.api,
                        "--web",
                        args.web,
                    ),
                    work_dir=root,
                ),
                SmokeCommand(
                    name="quality_report",
                    command=(
                        sys.executable,
                        "scripts/quality_report.py",
                        "--format",
                        "markdown",
                    ),
                    work_dir=root,
                ),
                SmokeCommand(
                    name="visual",
                    command=(
                        sys.executable,
                        "scripts/smoke_visual.py",
                        "--web",
                        args.web,
                        "--out-dir",
                        str(package_dir / "visual" / "artifacts"),
                    ),
                    work_dir=root,
                ),
                SmokeCommand(
                    name="ui_flow",
                    command=(
                        sys.executable,
                        "scripts/smoke_ui_flow.py",
                        "--web",
                        args.web,
                        "--symbol",
                        args.symbol,
                        "--out-dir",
                        str(package_dir / "ui_flow" / "artifacts"),
                    ),
                    work_dir=root,
                ),
            ]
        )
    commands.append(
        SmokeCommand(
            name="ui_mutation",
            command=(
                sys.executable,
                "scripts/smoke_ui_mutation.py",
                "--out-dir",
                str(package_dir / "ui_mutation" / "artifacts"),
            ),
            work_dir=root,
        )
    )
    return tuple(commands)


def _run_one(
    smoke: SmokeCommand,
    package_dir: Path,
    timeout: float,
    runner: CommandRunner,
) -> SmokeRun:
    run_dir = package_dir / smoke.name
    run_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = run_dir / "stdout.txt"
    stderr_path = run_dir / "stderr.txt"
    started = time.monotonic()
    try:
        completed = runner(smoke.command, timeout)
        returncode = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except Exception as exc:
        returncode = 1
        stdout = ""
        stderr = str(exc)
    duration = time.monotonic() - started
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    return SmokeRun(
        name=smoke.name,
        status="passed" if returncode == 0 else "failed",
        returncode=returncode,
        duration_seconds=round(duration, 3),
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        command=smoke.command,
        artifacts=_collect_artifacts(run_dir, package_dir),
    )


def _run_command(command: Sequence[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout,
    )


def _collect_artifacts(run_dir: Path, package_dir: Path) -> tuple[dict[str, object], ...]:
    artifacts: list[dict[str, object]] = []
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file()):
        artifacts.append(
            {
                "path": str(path.relative_to(package_dir)),
                "size_bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return tuple(artifacts)


def _write_manifest(args: ReleaseArgs, result: ReleaseResult) -> None:
    manifest = {
        "run_id": result.run_id,
        "generated_at": _utc_now(),
        "status": result.status,
        "api": args.api,
        "web": args.web,
        "symbol": args.symbol,
        "skip_live": args.skip_live,
        "runs": [
            {
                "name": run.name,
                "status": run.status,
                "returncode": run.returncode,
                "duration_seconds": run.duration_seconds,
                "command": list(run.command),
                "stdout": str(run.stdout_path.relative_to(result.package_dir)),
                "stderr": str(run.stderr_path.relative_to(result.package_dir)),
                "artifacts": list(run.artifacts),
            }
            for run in result.runs
        ],
    }
    (result.package_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_summary(args: ReleaseArgs, result: ReleaseResult) -> None:
    lines = [
        f"# Noesis Release Smoke {result.run_id}",
        "",
        f"- status: {result.status}",
        f"- api: {args.api}",
        f"- web: {args.web}",
        f"- symbol: {args.symbol}",
        f"- generated_at: {_utc_now()}",
        "",
        "| Smoke | Status | Return Code | Duration | Stdout |",
        "|---|---|---:|---:|---|",
    ]
    for run in result.runs:
        lines.append(
            "| "
            f"{run.name} | {run.status} | {run.returncode} | "
            f"{run.duration_seconds:.2f}s | {run.stdout_path.relative_to(result.package_dir)} |"
        )
    lines.append("")
    (result.package_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def _timestamp_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
