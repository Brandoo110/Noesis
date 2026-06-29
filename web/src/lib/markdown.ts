import type { StockDetailData } from "../hooks/use-stock-detail";
import type {
  Edge,
  IntelItem,
  OverlapGroup,
  PortfolioBrief,
  Thesis,
  ThesisAssumption
} from "../types/api";

const RELATION_LABELS: Record<Edge["relation"], string> = {
  supplier: "供应商",
  customer: "客户",
  competitor: "竞品",
  belongs_to: "所属主题"
};

const KIND_LABELS: Record<ThesisAssumption["kind"], string> = {
  reason: "持有理由",
  assumption: "关键假设",
  risk: "风险"
};

export function stockReportToMarkdown(detail: StockDetailData): string {
  const symbol = detail.entity?.symbol ?? detail.entityId;
  return [
    `# ${symbol} 深度报告`,
    section("① 摘要", summaryLines(detail)),
    section("② 变化", intelChangeLines(detail.intelItems)),
    section("③ 产业链", chainLines(detail.neighbors)),
    section("④ 分类情报", intelLines(detail.intelItems)),
    section("⑤ 方向", sentimentLines(detail.intelItems)),
    section("⑥ Thesis", thesisLines(detail.thesis)),
    section("⑦ 关注点（仅供参考）", attentionLines(detail.thesis)),
    section("⑧ 来源清单", evidenceLines(detail))
  ].join("\n\n");
}

export function portfolioBriefToMarkdown(brief: PortfolioBrief): string {
  return [
    "# 组合 Brief",
    "仅供参考：以下内容用于研究跟踪，保留来源与推断标记。",
    section("运行健康", briefRunHealthLines(brief)),
    section("持仓一句话", briefPositionLines(brief)),
    section("产业段重叠", briefOverlapLines(brief.overlaps))
  ].join("\n\n");
}

export function downloadMarkdown(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function briefPositionLines(brief: PortfolioBrief): string[] {
  if (brief.positions.length === 0) {
    return ["- 暂无持仓 Brief。"];
  }
  return brief.positions.map(
    (position) =>
      `- **${position.symbol}**: ${position.thesis_summary ?? "尚未研究"}`
  );
}

function briefOverlapLines(overlaps: OverlapGroup[]): string[] {
  if (overlaps.length === 0) {
    return ["- 暂无产业段重叠。"];
  }
  return overlaps.map((group) => {
    const symbols = group.positions.map((position) => position.symbol).join(" / ");
    const basis = group.basis === "inferred" ? "基于推断" : "有出处";
    return `- ${group.segment_name}: ${symbols}（${basis}）`;
  });
}

function briefRunHealthLines(brief: PortfolioBrief): string[] {
  const health = brief.run_health;
  return [
    `- latest runs: ${health.total_latest_runs}`,
    `- failed: ${health.failed}`,
    `- degraded: ${health.degraded_runs}`,
    `- completed without thesis: ${health.completed_without_thesis}`,
    ...health.failed_runs.map(
      (run) =>
        `- failed run ${run.symbol || run.position_id}: ${run.reason ?? run.status}`
    ),
    ...health.degraded_reasons.map(
      (item) => `- degraded reason ${item.reason}: ${item.count}`
    )
  ];
}

function section(title: string, lines: string[]): string {
  return [`## ${title}`, ...lines].join("\n");
}

function summaryLines(detail: StockDetailData): string[] {
  const name = detail.entity?.name ?? detail.entityId;
  return [detail.thesis?.summary ?? `${name} 暂无综合 thesis。`];
}

function intelChangeLines(items: IntelItem[]): string[] {
  if (items.length === 0) {
    return ["- 暂无变化情报。"];
  }
  return items.map((item) => `- ${item.title}: ${item.content}`);
}

function chainLines(edges: Edge[]): string[] {
  if (edges.length === 0) {
    return ["- 暂无产业链边。"];
  }
  return edges.map((edge) => {
    const inferred = edge.basis === "inferred" ? " (基于推断)" : "";
    return [
      `- ${RELATION_LABELS[edge.relation]}: ${edge.to_name}${inferred}`,
      `confidence ${Math.round(edge.confidence * 100)}%`
    ].join("；");
  });
}

function intelLines(items: IntelItem[]): string[] {
  if (items.length === 0) {
    return ["- 暂无情报。"];
  }
  return items.map(
    (item) =>
      `- ${item.title}（${item.event_type} / ${item.sentiment.dir} / tier ${item.source_tier}）：${item.content}`
  );
}

function sentimentLines(items: IntelItem[]): string[] {
  if (items.length === 0) {
    return ["- 暂无方向信号。"];
  }
  const counts = items.reduce(
    (current, item) => ({
      ...current,
      [item.sentiment.dir]: current[item.sentiment.dir] + 1
    }),
    { up: 0, down: 0, neutral: 0 }
  );
  return [
    `- up: ${counts.up}`,
    `- down: ${counts.down}`,
    `- neutral: ${counts.neutral}`
  ];
}

function thesisLines(thesis: Thesis | null): string[] {
  if (!thesis) {
    return ["- 暂无 thesis。"];
  }
  return [
    `- 摘要：${thesis.summary}`,
    ...(["reason", "assumption", "risk"] as const).flatMap((kind) => {
      const assumptions = thesis.assumptions.filter((item) => item.kind === kind);
      return assumptions.length === 0
        ? [`- ${KIND_LABELS[kind]}：暂无。`]
        : assumptions.map((item) => `- ${KIND_LABELS[kind]}：${item.text}`);
    })
  ];
}

function attentionLines(thesis: Thesis | null): string[] {
  const risks = thesis?.assumptions.filter((item) => item.kind === "risk") ?? [];
  if (risks.length === 0) {
    return ["- 仅供参考：暂无关注点。"];
  }
  return risks.map((risk) => `- 仅供参考：${risk.text}`);
}

function evidenceLines(detail: StockDetailData): string[] {
  if (detail.evidences.length === 0) {
    return ["- 暂无来源。"];
  }
  return detail.evidences.map((evidence) => {
    const title = evidence.title ?? evidence.id;
    const url = evidence.url ?? "无链接";
    return `- ${title} - ${url} - tier ${evidence.source_tier}`;
  });
}
