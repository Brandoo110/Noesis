import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ComponentType, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "./api/client";
import { App } from "./App";
import {
  makeEntity,
  makeEvidence,
  makeOverlapGroup,
  makePosition,
  makeRunDetail,
  makeRunHealth
} from "./test/m3-fixtures";
import { REDLINE_PATTERN } from "./test/redline";
import type { Position } from "./types/api";

vi.mock("reactflow", async () => ({
  default: ({ nodeTypes, nodes }: FlowProps) => (
    <div data-testid="react-flow">
      {nodes.map((node) => {
        const Node = nodeTypes[node.type ?? "entity"];
        return (
          <Node
            data={node.data}
            dragging={false}
            id={node.id}
            isConnectable={false}
            key={node.id}
            selected={false}
            type={node.type}
            xPos={0}
            yPos={0}
            zIndex={0}
          />
        );
      })}
    </div>
  ),
  Background: () => null,
  Controls: () => null,
  Handle: ({ "data-testid": testId, type }: HandleProps) => (
    <span data-testid={testId} data-type={type} />
  ),
  Position: { Left: "left", Right: "right" },
  ReactFlowProvider: ({ children }: { children: ReactNode }) => <>{children}</>
}));

vi.mock("./api/client", () => ({
  confirmThesis: vi.fn(),
  createPosition: vi.fn(),
  expandEntity: vi.fn(),
  getEvidence: vi.fn(),
  getNeighbors: vi.fn(),
  getOverlaps: vi.fn(),
  getPortfolioBrief: vi.fn(),
  getRelevance: vi.fn(),
  getRepresentatives: vi.fn(),
  getRun: vi.fn(),
  listPositions: vi.fn(),
  startRun: vi.fn()
}));

interface FlowProps {
  nodeTypes: Record<string, ComponentType<Record<string, unknown>>>;
  nodes: Array<{ id: string; type?: string; data: unknown }>;
}

interface HandleProps {
  "data-testid"?: string;
  type: string;
}

interface DownloadCapture {
  anchor: HTMLAnchorElement;
  blobs: Blob[];
  restore: () => void;
}

const createPositionMock = vi.mocked(client.createPosition);
const getNeighborsMock = vi.mocked(client.getNeighbors);
const getOverlapsMock = vi.mocked(client.getOverlaps);
const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);
const getRelevanceMock = vi.mocked(client.getRelevance);
const getRunMock = vi.mocked(client.getRun);
const listPositionsMock = vi.mocked(client.listPositions);
const startRunMock = vi.mocked(client.startRun);

describe("App report export integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("exports the stock report markdown after a researched holding", async () => {
    setupResearchMocks();
    render(<App />);

    await addHolding("AAPL", "Apple");
    fireEvent.click(screen.getByRole("button", { name: "开始研究 AAPL" }));
    fireEvent.click(await screen.findByRole("button", { name: "查看图谱 AAPL" }));
    fireEvent.click(await screen.findByRole("button", { name: "详情 AAPL" }));
    fireEvent.click(await screen.findByRole("button", { name: "查看报告" }));

    const capture = installDownloadCapture();
    const report = screen.getByLabelText("个股深度报告");
    fireEvent.click(within(report).getByRole("button", { name: "导出 Markdown" }));

    const markdown = await readBlobText(capture.blobs[0]);
    expect(capture.anchor.download).toBe("AAPL-report.md");
    expect(capture.anchor.click).toHaveBeenCalledTimes(1);
    expect(markdown).toContain("# AAPL 深度报告");
    expect(markdown).toContain("## ① 摘要");
    expect(markdown).toContain("## ② 变化");
    expect(markdown).toContain("## ③ 产业链");
    expect(markdown).toContain("## ④ 分类情报");
    expect(markdown).toContain("## ⑤ 方向");
    expect(markdown).toContain("## ⑥ Thesis");
    expect(markdown).toContain("## ⑦ 关注点（仅供参考）");
    expect(markdown).toContain("## ⑧ 来源清单");
    expect(markdown).toContain("https://example.com/evidence-1");
    expect(markdown).not.toMatch(REDLINE_PATTERN);
    capture.restore();
  });

  it("exports the portfolio brief markdown from the portfolio home", async () => {
    setupResearchMocks();
    render(<App />);

    await addHolding("AAPL", "Apple");
    const capture = installDownloadCapture();
    const brief = await screen.findByLabelText("组合 Brief");
    fireEvent.click(within(brief).getByRole("button", { name: "导出 Markdown" }));

    const markdown = await readBlobText(capture.blobs[0]);
    expect(capture.anchor.download).toBe("portfolio-brief.md");
    expect(capture.anchor.click).toHaveBeenCalledTimes(1);
    expect(markdown).toContain("# 组合 Brief");
    expect(markdown).toContain("- **AAPL**: Apple supplier pressure is easing.");
    expect(markdown).toContain("Consumer Electronics");
    expect(markdown).toContain("仅供参考");
    expect(markdown).not.toMatch(REDLINE_PATTERN);
    capture.restore();
  });
});

async function addHolding(symbol: string, name: string): Promise<void> {
  fireEvent.change(screen.getByLabelText("Symbol"), { target: { value: symbol } });
  fireEvent.change(screen.getByLabelText("Name"), { target: { value: name } });
  fireEvent.click(screen.getByRole("button", { name: "新增持仓" }));
  await screen.findByText(symbol);
}

function setupResearchMocks(): void {
  let positions: Position[] = [];
  const entity = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
  const evidence = makeEvidence();
  const position = makePosition();
  const overlap = makeOverlapGroup();
  listPositionsMock.mockImplementation(async () => positions);
  createPositionMock.mockImplementation(async () => {
    positions = [position];
    return position;
  });
  startRunMock.mockResolvedValue({
    run_id: "run-1",
    status: "awaiting_confirmation",
    thesis_id: "thesis-1"
  });
  getRunMock.mockResolvedValue(makeRunDetail(entity, evidence));
  getNeighborsMock.mockResolvedValue({ entity_id: entity.id, edges: [] });
  getOverlapsMock.mockResolvedValue([overlap]);
  getPortfolioBriefMock.mockImplementation(async () => ({
    generated_at: "2026-06-28T00:00:00Z",
    positions: positions.map((item) => ({
      position_id: item.id,
      symbol: item.symbol,
      name: item.name,
      thesis_summary: "Apple supplier pressure is easing.",
      thesis_status: "confirmed"
    })),
    overlaps: [overlap],
    run_health: makeRunHealth({ total_latest_runs: positions.length })
  }));
  getRelevanceMock.mockResolvedValue({
    entity_id: entity.id,
    position_id: position.id,
    path: [entity]
  });
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
