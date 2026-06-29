#!/usr/bin/env python3
"""Generate a Noesis local data quality report."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from noesis.config.settings import Settings
from noesis.db.connection import connect
from noesis.db.migrate import migrate
from noesis.eval.quality import QualityFormat, build_quality_report, format_quality_report


@dataclass(frozen=True)
class QualityArgs:
    db_path: str | None
    format: QualityFormat
    fail_on_blockers: bool
    fail_on_warnings: bool


def parse_args(argv: Sequence[str] | None = None) -> QualityArgs:
    parser = argparse.ArgumentParser(description="Generate Noesis data quality report")
    parser.add_argument("--db-path", default=None)
    parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
    )
    parser.add_argument(
        "--fail-on-blockers",
        action="store_true",
        help="return exit code 1 when the quality report has release blockers",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="return exit code 1 when the quality report has warnings",
    )
    parsed = parser.parse_args(argv)
    return QualityArgs(
        db_path=parsed.db_path,
        format=cast(QualityFormat, parsed.format),
        fail_on_blockers=bool(parsed.fail_on_blockers),
        fail_on_warnings=bool(parsed.fail_on_warnings),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    db_path = args.db_path or Settings().db_path
    conn = connect(db_path)
    try:
        migrate(conn)
        report = build_quality_report(conn)
    finally:
        conn.close()
    print(format_quality_report(report, output_format=args.format))
    if args.fail_on_blockers and report.status == "blocked":
        return 1
    if args.fail_on_warnings and report.status != "passed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
