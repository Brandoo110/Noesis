import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import {
  makeAgentOpsRunList,
  makeMetricsSummary,
  makeRunTrace
} from "../../test/agentops-fixtures";
import { AgentOpsView } from "./AgentOpsView";

vi.mock("../../api/client", () => ({
  getMetricsSummary: vi.fn(),
  getRunTrace: vi.fn(),
  listRuns: vi.fn()
}));

const getMetricsSummaryMock = vi.mocked(client.getMetricsSummary);
const getRunTraceMock = vi.mocked(client.getRunTrace);
const listRunsMock = vi.mocked(client.listRuns);

describe("AgentOpsView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listRunsMock.mockResolvedValue({
      runs: [{
        ...makeAgentOpsRunList().runs[0],
        cache_hit_rate: 0.5,
        evidence_count: 1,
        latency_ms: 3000,
        run_id: "run-agentops",
        started_at: "2026-07-03T00:00:00Z",
        status: "completed",
        tool_count: 2
      }]
    });
    getMetricsSummaryMock.mockResolvedValue(makeMetricsSummary());
    getRunTraceMock.mockResolvedValue(makeRunTrace("run-agentops"));
  });

  it("renders the real AgentOps dashboard from API data", async () => {
    render(<AgentOpsView />);

    const dashboard = await screen.findByLabelText("AgentOps Dashboard");
    expect(within(dashboard).getAllByText("run-agentops").length).toBeGreaterThan(0);
    expect(listRunsMock).toHaveBeenCalled();
    expect(getMetricsSummaryMock).toHaveBeenCalled();
    await waitFor(() => expect(getRunTraceMock).toHaveBeenCalledWith("run-agentops"));
  });
});
