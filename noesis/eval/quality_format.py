import json

from noesis.eval.quality import QualityFormat, QualityReport


def format_quality_payload(
    report: QualityReport,
    *,
    output_format: QualityFormat,
) -> str:
    if output_format == "json":
        return _format_json(report)
    if output_format == "markdown":
        return _format_markdown(report)
    return _format_text(report)


def _format_text(report: QualityReport) -> str:
    lines = [
        "Noesis data quality report",
        f"status={report.status}",
        f"total_positions={report.total_positions}",
        f"latest_seed_runs={report.latest_seed_runs}",
        f"evidence_total={report.evidence_total}",
        f"status_counts={report.status_counts}",
        f"source_tier_counts={report.source_tier_counts}",
    ]
    for blocker in report.blockers:
        lines.append(f"blocker={blocker}")
    for warning in report.warnings:
        lines.append(f"warning={warning}")
    return "\n".join(lines)


def _format_json(report: QualityReport) -> str:
    payload = {
        "status": report.status,
        "total_positions": report.total_positions,
        "latest_seed_runs": report.latest_seed_runs,
        "status_counts": report.status_counts,
        "evidence_total": report.evidence_total,
        "source_tier_counts": {
            str(tier): count for tier, count in report.source_tier_counts.items()
        },
        "runs_without_evidence": list(report.runs_without_evidence),
        "runs_without_thesis": list(report.runs_without_thesis),
        "completed_runs_without_evidence": list(report.completed_runs_without_evidence),
        "completed_runs_without_thesis": list(report.completed_runs_without_thesis),
        "pending_runs_without_evidence": list(report.pending_runs_without_evidence),
        "pending_runs_without_thesis": list(report.pending_runs_without_thesis),
        "degraded_reason_counts": report.degraded_reason_counts,
        "failed_runs": [
            {"symbol": symbol, "run_id": run_id, "reason": reason}
            for symbol, run_id, reason in report.failed_runs
        ],
        "blockers": list(report.blockers),
        "warnings": list(report.warnings),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _format_markdown(report: QualityReport) -> str:
    lines = [
        "# Noesis data quality report",
        "",
        f"status: `{report.status}`",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| total_positions | {report.total_positions} |",
        f"| latest_seed_runs | {report.latest_seed_runs} |",
        f"| evidence_total | {report.evidence_total} |",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in report.blockers)
    if not report.blockers:
        lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in report.warnings)
    if not report.warnings:
        lines.append("- none")
    lines.extend(["", "## Status Counts", ""])
    lines.extend(f"- {status}: {count}" for status, count in report.status_counts.items())
    lines.extend(["", "## Source Tier Counts", ""])
    if report.source_tier_counts:
        lines.extend(
            f"- tier {tier}: {count}"
            for tier, count in report.source_tier_counts.items()
        )
    else:
        lines.append("- none")
    if report.failed_runs:
        lines.extend(["", "## Failed Runs", ""])
        lines.extend(
            f"- {symbol} {run_id}: {reason or 'unknown'}"
            for symbol, run_id, reason in report.failed_runs
        )
    return "\n".join(lines)
