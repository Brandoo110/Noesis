import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import * as markdown from "../../lib/markdown";
import { makeOverlapGroup } from "../../test/m3-fixtures";
import { REDLINE_PATTERN } from "../../test/redline";
import type { PortfolioBrief as PortfolioBriefData } from "../../types/api";
import { PortfolioBrief } from "./PortfolioBrief";

vi.mock("../../api/client", () => ({
  getPortfolioBrief: vi.fn()
}));

const getPortfolioBriefMock = vi.mocked(client.getPortfolioBrief);

describe("PortfolioBrief", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders positions and overlaps with a research-only tone", async () => {
    getPortfolioBriefMock.mockResolvedValue(makeBrief());

    render(<PortfolioBrief />);

    const brief = await screen.findByLabelText("组合 Brief");

    expect(within(brief).getByText("仅供参考")).toBeInTheDocument();
    expect(within(brief).getByText("AAPL")).toBeInTheDocument();
    expect(
      within(brief).getByText("Apple supplier pressure is easing.")
    ).toBeInTheDocument();
    expect(within(brief).getByText("MSFT")).toBeInTheDocument();
    expect(within(brief).getByText("尚未研究")).toBeInTheDocument();
    expect(within(brief).getByText("Consumer Electronics")).toBeInTheDocument();
    expect(within(brief).getByText("AAPL / MSFT")).toBeInTheDocument();
    expect(within(brief).getByText("基于推断")).toBeInTheDocument();
    expect(brief.textContent).not.toMatch(REDLINE_PATTERN);
  });

  it("exports the portfolio brief as markdown", async () => {
    const portfolioBriefToMarkdown = vi
      .spyOn(markdown, "portfolioBriefToMarkdown")
      .mockReturnValue("# 组合 Brief");
    const downloadMarkdown = vi
      .spyOn(markdown, "downloadMarkdown")
      .mockImplementation(() => undefined);
    getPortfolioBriefMock.mockResolvedValue(makeBrief());

    render(<PortfolioBrief />);

    await screen.findByText("AAPL");
    fireEvent.click(screen.getByRole("button", { name: "导出 Markdown" }));

    expect(portfolioBriefToMarkdown).toHaveBeenCalledWith(makeBrief());
    expect(downloadMarkdown).toHaveBeenCalledWith(
      "portfolio-brief.md",
      "# 组合 Brief"
    );
  });

  it("reloads when refreshKey changes", async () => {
    getPortfolioBriefMock.mockResolvedValueOnce({
      ...makeBrief(),
      positions: []
    });
    getPortfolioBriefMock.mockResolvedValueOnce(makeBrief());

    const { rerender } = render(<PortfolioBrief refreshKey={0} />);

    expect(await screen.findByText("暂无持仓 Brief")).toBeInTheDocument();
    rerender(<PortfolioBrief refreshKey={1} />);

    expect(await screen.findByText("AAPL")).toBeInTheDocument();
    expect(getPortfolioBriefMock).toHaveBeenCalledTimes(2);
  });
});

function makeBrief(): PortfolioBriefData {
  return {
    generated_at: "2026-06-28T00:00:00Z",
    positions: [
      {
        position_id: "position-aapl",
        symbol: "AAPL",
        name: "Apple",
        thesis_summary: "Apple supplier pressure is easing.",
        thesis_status: "confirmed"
      },
      {
        position_id: "position-msft",
        symbol: "MSFT",
        name: null,
        thesis_summary: null,
        thesis_status: null
      }
    ],
    overlaps: [makeOverlapGroup()]
  };
}
