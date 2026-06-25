"""Run a real Noesis seed research smoke.

Requires .env keys for DEEPSEEK, LIGHT(GLM), RISK(Gemini), and TAVILY before
running. Command:
python scripts/smoke_real.py --symbol AAPL --market US
"""

from __future__ import annotations

import argparse
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from noesis.config.settings import Settings
from noesis.db.connection import connect, with_tx
from noesis.db.migrate import migrate
from noesis.db.models import PositionRow
from noesis.graph.runner import (
    RunSnapshot,
    build_graph_deps,
    get_run_snapshot,
    resume_run,
    start_run,
)
from noesis.graph.schemas import ConfirmationResult, EvidenceRecord, IntelItemDraft
from noesis.graph.state import GraphDeps
from noesis.tools.llm.router import LLMRouter
from noesis.tools.search.tavily import TavilySearchAdapter


@dataclass(frozen=True)
class SmokeArgs:
    symbol: str
    market: str


@dataclass(frozen=True)
class SmokeRuntime:
    deps: GraphDeps
    conn: sqlite3.Connection
    checkpoint_conn: sqlite3.Connection


def parse_args(argv: Sequence[str] | None = None) -> SmokeArgs:
    parser = argparse.ArgumentParser(description="Run Noesis real E2E smoke.")
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--market", default="US")
    parsed = parser.parse_args(argv)
    return SmokeArgs(symbol=parsed.symbol, market=parsed.market)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    settings = Settings()
    with TemporaryDirectory(prefix="noesis-smoke-") as tmp_dir:
        with _runtime(settings, Path(tmp_dir)) as runtime:
            position_id = _insert_position(args, runtime)
            started = start_run(position_id, runtime.deps)
            snapshot = get_run_snapshot(started.run_id, runtime.deps)
            _print_snapshot(snapshot)
            completed = started
            if started.status == "awaiting_confirmation":
                completed = resume_run(
                    started.run_id,
                    ConfirmationResult(status="confirmed"),
                    runtime.deps,
                )
            _print_final(completed.run_id, completed.thesis_id, runtime)
    return 0


@contextmanager
def _runtime(settings: Settings, tmp_path: Path) -> Iterator[SmokeRuntime]:
    conn = connect(tmp_path / "noesis.db")
    checkpoint_conn = sqlite3.connect(
        tmp_path / "checkpoints.db",
        check_same_thread=False,
    )
    try:
        migrate(conn)
        deps = build_graph_deps(
            conn=conn,
            checkpoint_conn=checkpoint_conn,
            chroma_dir=str(tmp_path / "chroma"),
            search=TavilySearchAdapter(settings.tavily_api_key),
            llm=LLMRouter.from_env(settings),
            now=_utc_now,
        )
        yield SmokeRuntime(deps=deps, conn=conn, checkpoint_conn=checkpoint_conn)
    finally:
        checkpoint_conn.close()
        conn.close()


def _insert_position(args: SmokeArgs, runtime: SmokeRuntime) -> str:
    now = _utc_now()
    position_id = f"position-{uuid4().hex}"
    with with_tx(runtime.conn):
        runtime.deps.repos.positions.insert(
            PositionRow(
                id=position_id,
                user_id="smoke-user",
                symbol=args.symbol,
                market=args.market,
                name=None,
                kind="owned",
                qty=None,
                cost_basis=None,
                created_at=now,
                updated_at=now,
            )
        )
    return position_id


def _print_snapshot(snapshot: RunSnapshot) -> None:
    entity = snapshot.resolved_entity
    if entity is None:
        print("entity: None")
    else:
        print(f"entity: {entity.name} identifiers={entity.identifiers}")
    _print_evidences(snapshot.evidences)
    _print_intel(snapshot.intel_items)
    _print_thesis(snapshot)


def _print_evidences(evidences: list[EvidenceRecord]) -> None:
    print(f"evidences: {len(evidences)}")
    for item in evidences[:3]:
        print(
            "evidence "
            f"tier={item.source_tier} url={item.url} snippet={_snippet(item.snippet)}"
        )


def _print_intel(items: list[IntelItemDraft]) -> None:
    print(f"intel_items: {len(items)}")
    for item in items:
        print(
            "intel "
            f"title={item.title} event_type={item.event_type} "
            f"sentiment={item.sentiment.dir} evidence_ids={item.evidence_ids}"
        )


def _print_thesis(snapshot: RunSnapshot) -> None:
    draft = snapshot.thesis_draft
    if draft is None:
        print("thesis_draft: None")
        return
    print(f"thesis_draft: {draft.summary}")
    for item in draft.assumptions:
        print(f"assumption: {item.text} evidence_ids={item.evidence_ids}")


def _print_final(run_id: str, thesis_id: str | None, runtime: SmokeRuntime) -> None:
    traces = runtime.deps.repos.traces.list_by_run(run_id)
    print("traces:")
    for trace in traces:
        suffix = ""
        if trace.status == "degraded":
            suffix = f" reason={trace.reason} fallback={trace.fallback_used}"
        print(f"- {trace.node_name}: {trace.status}{suffix}")
    thesis_status = None
    if thesis_id is not None:
        thesis = runtime.deps.repos.theses.get(thesis_id)
        thesis_status = thesis.status if thesis is not None else None
    run = runtime.deps.repos.runs.get(run_id)
    print(f"final_thesis_status: {thesis_status}")
    print(f"thesis_id_is_none: {thesis_id is None}")
    print(f"final_run_status: {run.status if run is not None else 'missing'}")


def _snippet(value: str) -> str:
    return value.replace("\n", " ")[:80]


def _utc_now() -> str:
    return "2026-06-26T00:00:00Z"


if __name__ == "__main__":
    raise SystemExit(main())
