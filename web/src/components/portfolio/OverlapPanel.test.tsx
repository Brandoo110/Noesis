import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import { makeOverlapGroup } from "../../test/m3-fixtures";
import { REDLINE_PATTERN } from "../../test/redline";
import { OverlapPanel } from "./OverlapPanel";

vi.mock("../../api/client", () => ({
  getOverlaps: vi.fn()
}));

const getOverlapsMock = vi.mocked(client.getOverlaps);

describe("OverlapPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders shared segment overlaps with basis labels", async () => {
    getOverlapsMock.mockResolvedValue([
      {
        segment_id: "segment-consumer",
        segment_name: "Consumer Electronics",
        node_type: "segment",
        basis: "inferred",
        positions: [
          {
            position_id: "position-aapl",
            symbol: "AAPL",
            entity_id: "entity-aapl",
            confidence: 0.9
          },
          {
            position_id: "position-msft",
            symbol: "MSFT",
            entity_id: "entity-msft",
            confidence: 0.7
          }
        ]
      }
    ]);

    render(<OverlapPanel />);

    const panel = await screen.findByTestId("overlap-panel");

    expect(panel.tagName.toLowerCase()).toBe("small");
    expect(within(panel).getByText("仅供参考")).toBeInTheDocument();
    expect(within(panel).getByText("Consumer Electronics")).toBeInTheDocument();
    expect(within(panel).getByText("AAPL / MSFT")).toBeInTheDocument();
    expect(within(panel).getByText("基于推断")).toBeInTheDocument();
    expect(panel.textContent).not.toMatch(REDLINE_PATTERN);
  });

  it("shows an empty overlap state", async () => {
    getOverlapsMock.mockResolvedValue([]);

    render(<OverlapPanel />);

    const panel = await screen.findByTestId("overlap-panel");

    expect(within(panel).getByText("暂无产业段重叠")).toBeInTheDocument();
  });

  it("renders source-backed groups as sourced", async () => {
    getOverlapsMock.mockResolvedValue([
      {
        segment_id: "segment-cloud",
        segment_name: "Cloud Infrastructure",
        node_type: "theme",
        basis: "source_backed",
        positions: [
          {
            position_id: "position-msft",
            symbol: "MSFT",
            entity_id: "entity-msft",
            confidence: 0.8
          },
          {
            position_id: "position-googl",
            symbol: "GOOGL",
            entity_id: "entity-googl",
            confidence: 0.75
          }
        ]
      }
    ]);

    render(<OverlapPanel />);

    await waitFor(() =>
      expect(screen.getByText("有出处")).toBeInTheDocument()
    );
  });

  it("retries loading overlaps after an API failure", async () => {
    getOverlapsMock.mockRejectedValueOnce(
      new Error("GET /portfolio/overlaps failed: 503")
    );
    getOverlapsMock.mockResolvedValueOnce([makeOverlapGroup()]);

    render(<OverlapPanel />);

    expect(
      await screen.findByText("GET /portfolio/overlaps failed: 503")
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "重新加载重叠" }));

    expect(await screen.findByText("Consumer Electronics")).toBeInTheDocument();
    expect(getOverlapsMock).toHaveBeenCalledTimes(2);
  });

  it("reloads overlaps when refreshKey changes", async () => {
    getOverlapsMock.mockResolvedValueOnce([]);
    getOverlapsMock.mockResolvedValueOnce([makeOverlapGroup()]);

    const { rerender } = render(<OverlapPanel refreshKey={0} />);

    expect(await screen.findByText("暂无产业段重叠")).toBeInTheDocument();
    rerender(<OverlapPanel refreshKey={1} />);

    expect(await screen.findByText("Consumer Electronics")).toBeInTheDocument();
    expect(getOverlapsMock).toHaveBeenCalledTimes(2);
  });
});
