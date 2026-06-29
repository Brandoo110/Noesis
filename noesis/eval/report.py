import json
from dataclasses import dataclass
from typing import Literal, TypedDict, cast

from noesis.eval.metrics import EvalMetrics
from noesis.graph.state import GraphDeps

ReportFormat = Literal["text", "json", "markdown"]
EvalMode = Literal["from_db", "live"]
TraceStatus = Literal["started", "success", "degraded", "failed"]


class TraceSummary(TypedDict):
    total: int
    started: int
    success: int
    degraded: int
    failed: int


@dataclass(frozen=True)
class EvalCaseResult:
    symbol: str
    run_id: str | None
    status: str
    metrics: EvalMetrics | None
    trace_summary: TraceSummary


@dataclass(frozen=True)
class EvalReport:
    results: tuple[EvalCaseResult, ...]
    averages: EvalMetrics


def format_report(
    report: EvalReport,
    *,
    mode: EvalMode = "from_db",
    output_format: ReportFormat = "text",
) -> str:
    if output_format == "json":
        return _format_json_report(report, mode)
    if output_format == "markdown":
        return _format_markdown_report(report, mode)
    return _format_text_report(report, mode)


def trace_summary(run_id: str, deps: GraphDeps) -> TraceSummary:
    summary = empty_trace_summary()
    for trace in deps.repos.traces.list_by_run(run_id, conn=deps.repos.conn):
        summary["total"] += 1
        if trace.status in ("started", "success", "degraded", "failed"):
            summary[cast(TraceStatus, trace.status)] += 1
    return summary


def empty_trace_summary() -> TraceSummary:
    return {
        "total": 0,
        "started": 0,
        "success": 0,
        "degraded": 0,
        "failed": 0,
    }


def _format_text_report(report: EvalReport, mode: EvalMode) -> str:
    lines: list[str] = ["Noesis eval report", f"mode={mode}"]
    for result in report.results:
        if result.metrics is None:
            lines.append(f"case {result.symbol} status={result.status} run_id=None")
            continue
        lines.append(
            "case "
            f"{result.symbol} status={result.status} run_id={result.run_id} "
            f"grounding_rate={result.metrics['grounding_rate']:.2f} "
            f"redline_compliance={result.metrics['redline_compliance']:.2f} "
            f"basis_honesty={result.metrics['basis_honesty']:.2f} "
            f"anchor_rate={result.metrics['anchor_rate']:.2f} "
            f"trace_total={result.trace_summary['total']} "
            f"trace_degraded={result.trace_summary['degraded']} "
            f"trace_failed={result.trace_summary['failed']}"
        )
    lines.append(
        "average "
        f"grounding_rate={report.averages['grounding_rate']:.2f} "
        f"redline_compliance={report.averages['redline_compliance']:.2f} "
        f"basis_honesty={report.averages['basis_honesty']:.2f} "
        f"anchor_rate={report.averages['anchor_rate']:.2f}"
    )
    return "\n".join(lines)


def _format_json_report(report: EvalReport, mode: EvalMode) -> str:
    payload = {
        "mode": mode,
        "averages": dict(report.averages),
        "cases": [_case_payload(result) for result in report.results],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _format_markdown_report(report: EvalReport, mode: EvalMode) -> str:
    lines = [
        "# Noesis eval report",
        "",
        f"Mode: `{mode}`",
        "",
        "| Case | Status | Run | Grounding | Redline | Basis | Anchor | Traces total / degraded / failed |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for result in report.results:
        lines.append(_markdown_row(result))
    lines.extend(
        [
            "",
            "## Average",
            "",
            f"- grounding_rate: {report.averages['grounding_rate']:.2f}",
            f"- redline_compliance: {report.averages['redline_compliance']:.2f}",
            f"- basis_honesty: {report.averages['basis_honesty']:.2f}",
            f"- anchor_rate: {report.averages['anchor_rate']:.2f}",
        ]
    )
    return "\n".join(lines)


def _markdown_row(result: EvalCaseResult) -> str:
    traces = (
        f"{result.trace_summary['total']} / "
        f"{result.trace_summary['degraded']} / "
        f"{result.trace_summary['failed']}"
    )
    if result.metrics is None:
        return f"| {result.symbol} | {result.status} | - | - | - | - | - | {traces} |"
    return (
        f"| {result.symbol} | {result.status} | {result.run_id} | "
        f"{result.metrics['grounding_rate']:.2f} | "
        f"{result.metrics['redline_compliance']:.2f} | "
        f"{result.metrics['basis_honesty']:.2f} | "
        f"{result.metrics['anchor_rate']:.2f} | {traces} |"
    )


def _case_payload(result: EvalCaseResult) -> dict[str, object]:
    return {
        "symbol": result.symbol,
        "run_id": result.run_id,
        "status": result.status,
        "metrics": dict(result.metrics) if result.metrics is not None else None,
        "trace_summary": dict(result.trace_summary),
    }
