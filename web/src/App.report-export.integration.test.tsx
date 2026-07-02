import { fireEvent, render, screen, within } from "@testing-library/react";
import type { ComponentType, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "./api/client";
import { App } from "./App";
import {
  makeAgentOpsRunList,
  makeMetricsSummary,
  makeRunTrace
} from "./test/agentops-fixtures";
import {
  makeEntity,
  makeEvidence,
  makeOverlapGroup,
  makePosition,
  makeRunDetail,
  makeRunHealth
} from "./test/m3-fixtures";
import { REDLINE_PATTERN } from "./test/redline";

vi.mock("reactflow", () => ({
  default: ({ nodeTypes, nodes }: FlowProps) => (
    <div data-testid="react-flow">
      {nodes.map((node) => {
        const Node = nodeTypes[node.type ?? "entity"];
        return <Node data={node.data} id={node.id} key={node.id} selected={false} />;
      })}
    </div>
  ),
  Background: () => null,
  Controls: () => null,
  Handle: ({ "data-testid": testId }: { "data-testid"?: string }) => (
    <span data-testid={testId} />
  ),
  Position: { Left: "left", Right: "right" },
  ReactFlowProvider: ({ children }: { children: ReactNode }) => <>{children}</>
}));

vi.mock("./api/client", () => ({
  createPosition: vi.fn(),
  expandEntity: vi.fn(),
  getCorrelationMatrix: vi.fn(),
  getMetricsSummary: vi.fn(),
  getNeighbors: vi.fn(),
  getOverlaps: vi.fn(),
  getPortfolioBrief: vi.fn(),
  getRelevance: vi.fn(),
  getRun: vi.fn(),
  getRunTrace: vi.fn(),
  getSharedSuppliers: vi.fn(),
  listPositions: vi.fn(),
  listRuns: vi.fn()
}));

interface FlowProps {
  nodeTypes: Record<string, ComponentType<Record<string, unknown>>>;
  nodes: Array<{ id: string; type?: string; data: unknown }>;
}

interface DownloadCapture {
  anchor: HTMLAnchorElement;
  blobs: Blob[];
  restore: () => void;
}

const getCorrelationMatrixMock = vi.mocked(client.getCorrelationMatrix);
const getMetricsSummaryMock = vi.mocked(client.getMetricsSummary);
const getNeighborsMock = vi.mocked(client.getNeighbors);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const getRelevanceMock = vi.mocked(client.getRelevance);
const getRunMock = vi.mocked(client.getRun);
const getRunTraceMock = vi.mocked(client.getRunTrace);
const getSharedSuppliersMock = vi.mocked(client.getSharedSuppliers);
const listPositionsMock = vi.mocked(client.listPositions);
const listRunsMock = vi.mocked(client.listRuns);

describe("App report export integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("exports stock report and portfolio brief markdown from real views", async () => {
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "查看图谱 AAPL" }));
    fireEvent.click(await screen.findByRole("button", { name: "个股详情" }));
    fireEvent.click(await screen.findByRole("button", { name: "查看报告" }));

    const stockCapture = installDownloadCapture();
    fireEvent.click(
      within(screen.getByLabelText("个股深度报告")).getByRole("button", {
        name: "导出 Markdown"
      })
    );
    const stockMarkdown = await readBlobText(stockCapture.blobs[0]);
    expect(stockCapture.anchor.download).toBe("AAPL-report.md");
    expect(stockMarkdown).toContain("# AAPL 深度报告");
    expect(stockMarkdown).toContain("## ⑧ 来源清单");
    expect(stockMarkdown).toContain("https://example.com/evidence-1");
    expect(stockMarkdown).not.toMatch(REDLINE_PATTERN);
    stockCapture.restore();

    fireEvent.click(
      within(screen.getByRole("navigation", { name: "主导航" })).getByRole("button", {
        name: "组合工作台"
      })
    );
    const briefCapture = installDownloadCapture();
    fireEvent.click(
      within(await screen.findByLabelText("组合 Brief")).getByRole("button", {
        name: "导出 Markdown"
      })
    );
    const briefMarkdown = await readBlobText(briefCapture.blobs[0]);
    expect(briefCapture.anchor.download).toBe("portfolio-brief.md");
    expect(briefMarkdown).toContain("# 组合 Brief");
    expect(briefMarkdown).toContain("- **AAPL**: Apple supplier pressure is easing.");
    expect(briefMarkdown).toContain("仅供参考");
    expect(briefMarkdown).not.toMatch(REDLINE_PATTERN);
    briefCapture.restore();
  });
});

function setupMocks(): void {
  const entity = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
  const evidence = makeEvidence();
  const overlap = makeOverlapGroup();
  listPositionsMock.mockResolvedValue([
    makePosition({
      latest_run_entity: entity,
      latest_run_id: "run-1",
      latest_run_status: "awaiting_confirmation"
    })
  ]);
  getRunMock.mockResolvedValue(makeRunDetail(entity, evidence));
  getNeighborsMock.mockResolvedValue({ entity_id: entity.id, edges: [] });
  getOverlapsMock.mockResolvedValue([overlap]);
  getSharedSuppliersMock.mockResolvedValue([]);
  getCorrelationMatrixMock.mockResolvedValue({ positions: [], cells: [] });
  getPortfolioBriefMock.mockResolvedValue({
    generated_at: "2026-07-03T00:00:00Z",
    positions: [{
      position_id: "position-1",
      symbol: "AAPL",
      name: "Apple",
      thesis_summary: "Apple supplier pressure is easing.",
      thesis_status: "confirmed"
    }],
    overlaps: [overlap],
    run_health: makeRunHealth({ total_latest_runs: 1 })
  });
  getRelevanceMock.mockResolvedValue({ entity_id: entity.id, position_id: "position-1", path: [entity] });
  listRunsMock.mockResolvedValue(makeAgentOpsRunList());
  getMetricsSummaryMock.mockResolvedValue(makeMetricsSummary());
  getRunTraceMock.mockResolvedValue(makeRunTrace());
}

function installDownloadCapture(): DownloadCapture {
  const blobs: Blob[] = [];
  const anchor = document.createElement("a");
  vi.spyOn(anchor, "click").mockImplementation(() => undefined);
  const previousCreateObjectURL = URL.createObjectURL;
  const previousRevokeObjectURL = URL.revokeObjectURL;
  URL.createObjectURL = vi.fn((blob: Blob) => {
    blobs.push(blob);
    return "blob:report";
  });
  URL.revokeObjectURL = vi.fn();
  const originalCreateElement = document.createElement.bind(document);
  const createElement = vi.spyOn(document, "createElement");
  createElement.mockImplementation(((tagName: string, options?: ElementCreationOptions) => {
    if (tagName.toLowerCase() === "a") {
      return anchor;
    }
    return originalCreateElement(tagName, options);
  }) as typeof document.createElement);
  return {
    anchor,
    blobs,
    restore: () => {
      createElement.mockRestore();
      URL.createObjectURL = previousCreateObjectURL;
      URL.revokeObjectURL = previousRevokeObjectURL;
    }
  };
}

function readBlobText(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}
