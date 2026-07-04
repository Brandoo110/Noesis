from dataclasses import dataclass
from datetime import datetime
from typing import Literal


Severity = Literal["ok", "info", "warning", "critical"]
StepKind = Literal["node", "tool"]

SLOW_STEP_MS = 60_000


@dataclass(frozen=True)
class DiagnosticStep:
    name: str
    kind: StepKind
    status: str
    started_at: str
    ended_at: str | None
    latency_ms: int | None
    retry_count: int | None
    evidence_ids: list[str]


@dataclass(frozen=True)
class RunDiagnostic:
    severity: Severity
    title: str
    summary: str
    tags: list[str]
    slowest_step_name: str | None
    slowest_step_latency_ms: int | None
    last_step_name: str | None
    next_actions: list[str]
    has_degraded_step: bool
    has_failed_step: bool
    has_pending_confirmation: bool


def build_run_diagnostic(
    *,
    status: str,
    evidence_count: int,
    tool_count: int,
    steps: list[DiagnosticStep],
) -> RunDiagnostic:
    slowest = _slowest_step(steps)
    last_step = _last_step(steps)
    tags = diagnostic_tags(
        status=status,
        evidence_count=evidence_count,
        tool_count=tool_count,
        steps=steps,
    )
    failed_step = next((step for step in steps if step.status == "failed"), None)
    degraded_step = next((step for step in steps if step.status == "degraded"), None)
    slowest_latency = slowest.latency_ms if slowest is not None else None
    if failed_step is not None:
        return RunDiagnostic(
            severity="critical",
            title="当前 run 有失败步骤",
            summary=f"{failed_step.name} 失败，建议展开该步骤查看错误和重试信息。",
            tags=tags,
            slowest_step_name=slowest.name if slowest is not None else None,
            slowest_step_latency_ms=slowest_latency,
            last_step_name=last_step.name if last_step is not None else None,
            next_actions=["查看失败步骤详情", "检查工具错误和重试记录"],
            has_degraded_step=degraded_step is not None,
            has_failed_step=True,
            has_pending_confirmation=status == "awaiting_confirmation",
        )
    if status == "awaiting_confirmation":
        return RunDiagnostic(
            severity="info",
            title="当前 run 正在等待确认",
            summary="研究流程已暂停在人工确认环节，需要查看 thesis 草稿并确认。",
            tags=tags,
            slowest_step_name=slowest.name if slowest is not None else None,
            slowest_step_latency_ms=slowest_latency,
            last_step_name=last_step.name if last_step is not None else None,
            next_actions=["查看待确认 thesis", "确认或编辑研究假设"],
            has_degraded_step=degraded_step is not None,
            has_failed_step=False,
            has_pending_confirmation=True,
        )
    if degraded_step is not None:
        return RunDiagnostic(
            severity="warning",
            title="当前 run 已降级",
            summary=f"{degraded_step.name} 使用了降级路径，建议查看原因和 fallback。",
            tags=tags,
            slowest_step_name=slowest.name if slowest is not None else None,
            slowest_step_latency_ms=slowest_latency,
            last_step_name=last_step.name if last_step is not None else None,
            next_actions=["查看降级步骤详情", "核对证据和 fallback 输出"],
            has_degraded_step=True,
            has_failed_step=False,
            has_pending_confirmation=False,
        )
    if status == "completed" and evidence_count == 0:
        return _warning(
            "当前 run 缺少证据",
            "这次运行没有关联证据，建议查看搜索、检索和证据构建步骤。",
            tags,
            slowest,
            last_step,
        )
    if slowest_latency is not None and slowest_latency > SLOW_STEP_MS:
        return _warning(
            "当前 run 耗时偏高",
            f"最慢步骤是 {slowest.name}，建议展开查看 provider、retry 和输入输出摘要。",
            tags,
            slowest,
            last_step,
        )
    return RunDiagnostic(
        severity="ok",
        title="当前 run 未发现明显问题",
        summary="这次运行没有失败、降级、低证据或明显慢步骤。",
        tags=tags,
        slowest_step_name=slowest.name if slowest is not None else None,
        slowest_step_latency_ms=slowest_latency,
        last_step_name=last_step.name if last_step is not None else None,
        next_actions=["需要排查时可展开具体 step 查看输入、输出和证据"],
        has_degraded_step=False,
        has_failed_step=False,
        has_pending_confirmation=False,
    )


def diagnostic_tags(
    *,
    status: str,
    evidence_count: int,
    tool_count: int,
    steps: list[DiagnosticStep],
) -> list[str]:
    tags: list[str] = []
    slowest = _slowest_step(steps)
    if status == "awaiting_confirmation":
        tags.append("waiting_confirmation")
    if slowest is not None and slowest.latency_ms is not None:
        if slowest.latency_ms > SLOW_STEP_MS:
            tags.append("slow")
    if status == "completed" and evidence_count == 0:
        tags.append("low_evidence")
    if any(step.status == "degraded" for step in steps):
        tags.append("degraded")
    if any(step.status == "failed" for step in steps):
        tags.append("failed")
    if tool_count == 0:
        tags.append("no_tools")
    return tags


def _warning(
    title: str,
    summary: str,
    tags: list[str],
    slowest: DiagnosticStep | None,
    last_step: DiagnosticStep | None,
) -> RunDiagnostic:
    return RunDiagnostic(
        severity="warning",
        title=title,
        summary=summary,
        tags=tags,
        slowest_step_name=slowest.name if slowest is not None else None,
        slowest_step_latency_ms=slowest.latency_ms if slowest is not None else None,
        last_step_name=last_step.name if last_step is not None else None,
        next_actions=["查看相关 step 详情", "核对 evidence 和工具输出"],
        has_degraded_step=False,
        has_failed_step=False,
        has_pending_confirmation=False,
    )


def _slowest_step(steps: list[DiagnosticStep]) -> DiagnosticStep | None:
    candidates = [step for step in steps if step.latency_ms is not None]
    return max(candidates, key=lambda step: step.latency_ms or 0, default=None)


def _last_step(steps: list[DiagnosticStep]) -> DiagnosticStep | None:
    return max(steps, key=lambda step: _sort_time(step.ended_at or step.started_at), default=None)


def _sort_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
