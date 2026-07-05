import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { EvidenceDrawerProvider } from "../../context/evidence-drawer";
import type { Edge, EntityNode, ExpandResult, Relation } from "../../types/api";
import { GraphExplorer } from "./GraphExplorer";

vi.mock("reactflow", async () => {
  const React = await import("react");
  return {
    default: ({
      edges,
      nodes,
      nodeTypes
    }: {
      edges: Array<{ id: string; data: { edge?: Edge } }>;
      nodes: Array<{ id: string; type?: string; data: unknown }>;
      nodeTypes: Record<string, React.ComponentType<Record<string, unknown>>>;
    }) => (
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
        {edges.map((edge) => (
          <span data-testid={`flow-edge-${edge.id}`} key={edge.id}>
            {edge.data.edge?.basis}
          </span>
        ))}
      </div>
    ),
    Background: () => null,
    Controls: () => null,
    Handle: ({
      "data-testid": testId,
      type
    }: {
      "data-testid"?: string;
      type: string;
    }) => <span data-testid={testId} data-type={type} />,
    Position: {
      Left: "left",
      Right: "right"
    },
    ReactFlowProvider: ({ children }: { children: ReactNode }) => <>{children}</>
  };
});

vi.mock("../../api/client", () => ({
  expandEntity: vi.fn()
}));

vi.mock("../stock/StockDetail", () => ({
  StockDetail: ({
    entityId,
    positionId,
    runId
  }: {
    entityId: string;
    onClose?: () => void;
    positionId: string;
    runId: string;
  }) => (
    <aside aria-label="个股详情" role="dialog">
      {`${entityId}:${positionId}:${runId}`}
    </aside>
  )
}));

const expandEntityMock = vi.mocked(client.expandEntity);

describe("GraphExplorer", () => {
  it("opens detail from the seed node and expands through the seed badge", async () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
    const neighbor = makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" });
    expandEntityMock.mockResolvedValue(makeExpandResult("entity-aapl", [
      makeEdge("edge-aapl-tsm", neighbor)
    ]));

    const { container } = renderGraph(
      <GraphExplorer positionId="position-1" runId="run-1" seedEntity={seed} />
    );

    expect(screen.getByTestId("graph-stage")).toBeInTheDocument();
    expect(screen.queryByTestId("react-flow")).not.toBeInTheDocument();
    expect(screen.getByTestId("graph-node-entity-aapl")).toHaveClass("seed-node");
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.queryByText("TSM")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("graph-node-entity-aapl"));
    expect(screen.getByRole("dialog", { name: "个股详情" })).toHaveTextContent(
      "entity-aapl:position-1:run-1"
    );
    expect(expandEntityMock).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "调研 Apple Inc." }));

    await waitFor(() =>
      expect(expandEntityMock).toHaveBeenCalledWith("entity-aapl", "position-1")
    );
    expect(await screen.findByText("TSM")).toBeInTheDocument();
    expect(container.querySelectorAll(".edge-label-chip")).toHaveLength(0);
    expect(screen.getByTestId("edge-path-edge-aapl-tsm")).toHaveClass(
      "edge-relation-supplier"
    );
    expect(screen.getByTestId("edge-path-edge-aapl-tsm")).not.toHaveAttribute(
      "stroke-dasharray"
    );
    expect(screen.getByLabelText("关系类型图例")).toHaveTextContent("供应商");
    expect(screen.getByLabelText("关系清单")).toHaveTextContent("供应商");
    expect(screen.getByLabelText("关系清单")).toHaveTextContent("82%");
  });

  it("filters visible edges by basis and resets expanded graph", async () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
    const sourceNeighbor = makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" });
    const inferredNeighbor = makeEntity({
      id: "segment-consumer",
      name: "Consumer Electronics",
      node_type: "segment",
      symbol: null
    });
    expandEntityMock.mockResolvedValue(makeExpandResult("entity-aapl", [
      makeEdge("edge-source", sourceNeighbor, "source_backed"),
      makeEdge("edge-inferred", inferredNeighbor, "inferred")
    ]));

    renderGraph(<GraphExplorer positionId="position-1" runId="run-1" seedEntity={seed} />);

    fireEvent.click(screen.getByRole("button", { name: "调研 Apple Inc." }));
    expect(await screen.findByTestId("edge-path-edge-source")).toBeInTheDocument();
    expect(screen.getByTestId("edge-path-edge-inferred")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "source_backed" }));

    expect(screen.getByTestId("edge-path-edge-source")).toBeInTheDocument();
    expect(screen.queryByTestId("edge-path-edge-inferred")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "重置图谱" }));
    expect(screen.queryByText("TSM")).not.toBeInTheDocument();
    expect(screen.queryByText("Consumer Electronics")).not.toBeInTheDocument();
  });

  it("shows expand lifecycle states instead of hiding failed or empty results", async () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });
    const emptyResult = deferred<ExpandResult>();
    expandEntityMock.mockReturnValueOnce(emptyResult.promise);

    renderGraph(<GraphExplorer positionId="position-1" runId="run-1" seedEntity={seed} />);

    const researchButton = screen.getByRole("button", { name: "调研 Apple Inc." });
    expect(researchButton).toHaveTextContent("调研");
    fireEvent.click(researchButton);

    const loadingButton = screen.getByRole("button", { name: "调研中 Apple Inc." });
    expect(loadingButton).toHaveTextContent("调研中");
    expect(loadingButton).toBeDisabled();
    expect(screen.queryByText("...")).not.toBeInTheDocument();

    emptyResult.resolve(makeExpandResult("entity-aapl", []));

    expect(await screen.findByText("Apple Inc. 未发现新增一跳关系。")).toBeInTheDocument();
    expect(screen.getByLabelText("Apple Inc. 无新增关系")).toHaveTextContent("0");

    fireEvent.click(screen.getByRole("button", { name: "重置图谱" }));
    expandEntityMock.mockRejectedValueOnce(new Error("network down"));

    fireEvent.click(screen.getByRole("button", { name: "调研 Apple Inc." }));

    expect(await screen.findByText("Apple Inc. 展开失败：network down")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试调研 Apple Inc." })).toBeInTheDocument();

    const neighbor = makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" });
    expandEntityMock.mockResolvedValueOnce(makeExpandResult("entity-aapl", [
      makeEdge("edge-aapl-tsm", neighbor, "source_backed", "supplier")
    ], "cached"));

    fireEvent.click(screen.getByRole("button", { name: "重试调研 Apple Inc." }));

    expect(await screen.findByText("Apple Inc. 使用缓存结果，显示 1 条关系。")).toBeInTheDocument();
    expect(screen.getByLabelText("Apple Inc. 已展开 1 条关系")).toHaveTextContent("1");
  });

  it("filters by relation and supports node focus mode", async () => {
    const seed = makeEntity({ id: "entity-nvda", name: "NVIDIA Corp", symbol: "NVDA" });
    const supplier = makeEntity({ id: "entity-tsm", name: "TSMC", symbol: "TSM" });
    const competitor = makeEntity({ id: "entity-amd", name: "AMD", symbol: "AMD" });
    expandEntityMock.mockResolvedValue(makeExpandResult("entity-nvda", [
      makeEdge("edge-nvda-tsm", supplier, "source_backed", "supplier"),
      makeEdge("edge-nvda-amd", competitor, "source_backed", "competitor")
    ]));

    renderGraph(<GraphExplorer positionId="position-1" runId="run-1" seedEntity={seed} />);

    fireEvent.click(screen.getByRole("button", { name: "调研 NVIDIA Corp" }));
    expect(await screen.findByTestId("edge-path-edge-nvda-tsm")).toBeInTheDocument();
    expect(screen.getByTestId("edge-path-edge-nvda-amd")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "只看供应商关系" }));

    expect(screen.getByTestId("edge-path-edge-nvda-tsm")).toBeInTheDocument();
    expect(screen.queryByTestId("edge-path-edge-nvda-amd")).not.toBeInTheDocument();
    expect(screen.getByLabelText("关系清单")).toHaveTextContent("供应商");
    expect(screen.getByLabelText("关系清单")).not.toHaveTextContent("竞争");

    fireEvent.click(screen.getByRole("button", { name: "显示全部关系类型" }));
    fireEvent.click(screen.getByTestId("graph-node-entity-tsm"));

    expect(screen.getByText("聚焦：TSM")).toBeInTheDocument();
    expect(screen.getByTestId("edge-path-edge-nvda-tsm")).toBeInTheDocument();
    expect(screen.queryByTestId("edge-path-edge-nvda-amd")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("graph-stage"));

    expect(screen.queryByText("聚焦：TSM")).not.toBeInTheDocument();
    expect(screen.getByTestId("edge-path-edge-nvda-tsm")).toBeInTheDocument();
    expect(screen.getByTestId("edge-path-edge-nvda-amd")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("graph-node-entity-tsm"));
    expect(screen.getByText("聚焦：TSM")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "清除聚焦" }));

    expect(screen.getByTestId("edge-path-edge-nvda-tsm")).toBeInTheDocument();
    expect(screen.getByTestId("edge-path-edge-nvda-amd")).toBeInTheDocument();
  });

  it("keeps graph overlays fixed while the stage can zoom", () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });

    renderGraph(<GraphExplorer positionId="position-1" runId="run-1" seedEntity={seed} />);

    const canvas = screen.getByTestId("graph-canvas");
    const scrollPlane = screen.getByTestId("graph-scroll-plane");
    const legend = screen.getByLabelText("关系类型图例");
    expect(legend.parentElement).not.toBe(scrollPlane);
    expect(canvas.style.getPropertyValue("--graph-canvas-h")).toBe("560px");

    const stageShell = screen.getByTestId("graph-stage-shell");
    expect(stageShell.style.getPropertyValue("--graph-stage-scale")).toBe("1");

    fireEvent.click(screen.getByRole("button", { name: "放大图谱" }));

    expect(canvas.style.getPropertyValue("--graph-canvas-h")).toBe("560px");
    expect(stageShell.style.getPropertyValue("--graph-stage-scale")).toBe("1.15");
    expect(stageShell.style.getPropertyValue("--graph-stage-scaled-h")).toBe("644px");
    expect(screen.getByLabelText("当前缩放比例")).toHaveTextContent("115%");
  });

  it("supports trackpad pinch-style wheel zoom on the graph layer", async () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });

    renderGraph(<GraphExplorer positionId="position-1" runId="run-1" seedEntity={seed} />);

    const scrollPlane = screen.getByTestId("graph-scroll-plane");
    const stageShell = screen.getByTestId("graph-stage-shell");

    expect(stageShell.style.getPropertyValue("--graph-stage-scale")).toBe("1");

    const handled = fireEvent.wheel(scrollPlane, {
      bubbles: true,
      cancelable: true,
      clientX: 280,
      ctrlKey: true,
      deltaY: -90
    });

    expect(handled).toBe(false);
    await waitFor(() =>
      expect(Number(stageShell.style.getPropertyValue("--graph-stage-scale"))).toBeGreaterThan(1)
    );
    expect(screen.getByLabelText("当前缩放比例")).not.toHaveTextContent("100%");
  });

  it("opens stock detail in an overlay and closes it from the backdrop", async () => {
    const seed = makeEntity({ id: "entity-aapl", name: "Apple Inc.", symbol: "AAPL" });

    const { container } = renderGraph(
      <GraphExplorer positionId="position-1" runId="run-1" seedEntity={seed} />
    );

    fireEvent.click(screen.getByRole("button", { name: "个股详情" }));

    expect(screen.getByRole("dialog", { name: "个股详情" })).toHaveTextContent(
      "entity-aapl:position-1:run-1"
    );
    const backdrop = container.querySelector(".detail-layer .drawer-backdrop");
    expect(backdrop).not.toBeNull();
    fireEvent.click(backdrop as Element);
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: "个股详情" })).not.toBeInTheDocument()
    );
  });
});

function renderGraph(graph: JSX.Element): ReturnType<typeof render> {
  return render(<EvidenceDrawerProvider>{graph}</EvidenceDrawerProvider>);
}

function makeExpandResult(
  entityId: string,
  edges: Edge[],
  status: ExpandResult["status"] = "completed"
): ExpandResult {
  return {
    entity_id: entityId,
    run_id: `run-${entityId}`,
    status,
    edges
  };
}

function makeEdge(
  id: string,
  neighbor: EntityNode,
  basis: Edge["basis"] = "source_backed",
  relation: Relation = "supplier"
): Edge {
  return {
    id,
    to_entity_id: neighbor.id,
    to_name: neighbor.name,
    to_symbol: neighbor.symbol,
    relation,
    basis,
    confidence: 0.82,
    evidence_ids: ["evidence-1"],
    source_tier: 2,
    rationale: "Supplier relation is source-backed.",
    neighbor
  };
}

function deferred<T>(): { promise: Promise<T>; reject: (error: Error) => void; resolve: (value: T) => void } {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, reject, resolve };
}

function makeEntity(overrides: Partial<EntityNode> = {}): EntityNode {
  return {
    id: "entity-aapl",
    name: "Apple Inc.",
    node_type: "company",
    symbol: "AAPL",
    market: "US",
    ...overrides
  };
}
