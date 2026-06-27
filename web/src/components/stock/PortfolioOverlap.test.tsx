import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeOverlapGroup } from "../../test/m3-fixtures";
import { REDLINE_PATTERN } from "../../test/redline";
import { PortfolioOverlap } from "./PortfolioOverlap";

describe("PortfolioOverlap", () => {
  it("renders other holdings that share a segment with the current entity", () => {
    render(
      <PortfolioOverlap
        entityId="entity-aapl"
        overlaps={[makeOverlapGroup()]}
      />
    );

    const section = screen.getByLabelText("和其他持仓的关系");
    const notes = within(section).getByLabelText("组合重叠关系");

    expect(notes.tagName.toLowerCase()).toBe("small");
    expect(within(notes).getByText("仅供参考")).toBeInTheDocument();
    expect(within(notes).getByText("Consumer Electronics")).toBeInTheDocument();
    expect(within(notes).getByText("MSFT")).toBeInTheDocument();
    expect(within(notes).queryByText("AAPL")).not.toBeInTheDocument();
    expect(within(notes).getByText("基于推断")).toBeInTheDocument();
    expect(notes.textContent).not.toMatch(REDLINE_PATTERN);
  });

  it("shows an empty state when the current entity is not in any overlap group", () => {
    render(
      <PortfolioOverlap
        entityId="entity-tsm"
        overlaps={[makeOverlapGroup()]}
      />
    );

    expect(
      screen.getByText("与其他持仓无产业段重叠")
    ).toBeInTheDocument();
  });
});
