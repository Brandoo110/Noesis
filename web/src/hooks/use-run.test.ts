import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../api/client";
import type { RunDetail, RunStatus, RunSummary } from "../types/api";
import { useRun } from "./use-run";

vi.mock("../api/client", () => ({
  getRun: vi.fn(),
  startRun: vi.fn()
}));

const startRunMock = vi.mocked(client.startRun);
const getRunMock = vi.mocked(client.getRun);

describe("useRun", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts a run and polls until awaiting confirmation", async () => {
    startRunMock.mockResolvedValue(
      makeRunSummary({ run_id: "run-1", status: "running" })
    );
    getRunMock.mockResolvedValueOnce(makeRunDetail({ status: "running" }));
    getRunMock.mockResolvedValueOnce(
      makeRunDetail({
        status: "awaiting_confirmation",
        thesis_id: "thesis-1",
        entity: {
          id: "entity-aapl",
          name: "Apple Inc.",
          node_type: "company",
          symbol: "AAPL",
          market: "US"
        }
      })
    );

    const { result } = renderHook(() => useRun({ pollMs: 100 }));

    await act(async () => {
      await result.current.start("position-1");
    });

    expect(startRunMock).toHaveBeenCalledWith("position-1");
    expect(result.current.status).toBe("running");
    expect(result.current.runId).toBe("run-1");
    expect(result.current.thesisId).toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(getRunMock).toHaveBeenCalledWith("run-1");
    expect(result.current.status).toBe("running");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(result.current.status).toBe("awaiting_confirmation");
    expect(result.current.thesisId).toBe("thesis-1");
    expect(result.current.entityId).toBe("entity-aapl");
  });

  it("loads run detail immediately when start returns awaiting confirmation", async () => {
    startRunMock.mockResolvedValue(
      makeRunSummary({
        run_id: "run-1",
        status: "awaiting_confirmation",
        thesis_id: "thesis-1"
      })
    );
    getRunMock.mockResolvedValue(
      makeRunDetail({
        status: "awaiting_confirmation",
        thesis_id: "thesis-1",
        entity: {
          id: "entity-aapl",
          name: "Apple Inc.",
          node_type: "company",
          symbol: "AAPL",
          market: "US"
        }
      })
    );

    const { result } = renderHook(() => useRun({ pollMs: 100 }));

    await act(async () => {
      await result.current.start("position-1");
    });

    expect(getRunMock).toHaveBeenCalledWith("run-1");
    expect(result.current.entityId).toBe("entity-aapl");
  });

  it("refreshes the current run detail", async () => {
    startRunMock.mockResolvedValue(
      makeRunSummary({
        run_id: "run-1",
        status: "awaiting_confirmation",
        thesis_id: "thesis-1"
      })
    );
    getRunMock.mockResolvedValueOnce(
      makeRunDetail({
        status: "awaiting_confirmation",
        thesis_id: "thesis-1",
        entity: {
          id: "entity-aapl",
          name: "Apple Inc.",
          node_type: "company",
          symbol: "AAPL",
          market: "US"
        }
      })
    );
    getRunMock.mockResolvedValueOnce(
      makeRunDetail({
        status: "completed",
        thesis_id: "thesis-1",
        entity: {
          id: "entity-aapl",
          name: "Apple Inc.",
          node_type: "company",
          symbol: "AAPL",
          market: "US"
        }
      })
    );

    const { result } = renderHook(() => useRun({ pollMs: 100 }));

    await act(async () => {
      await result.current.start("position-1");
    });
    await act(async () => {
      await result.current.refresh();
    });

    expect(getRunMock).toHaveBeenLastCalledWith("run-1");
    expect(result.current.status).toBe("completed");
  });
});

function makeRunSummary(overrides: Partial<RunSummary> = {}): RunSummary {
  return {
    run_id: "run-1",
    status: "running",
    thesis_id: null,
    ...overrides
  };
}

function makeRunDetail(
  overrides: Partial<Pick<RunDetail, "status" | "thesis_id" | "entity">> = {}
): RunDetail {
  return {
    run_id: "run-1",
    status: "running" satisfies RunStatus,
    thesis_id: null,
    entity: null,
    evidences: [],
    intel_items: [],
    thesis: null,
    ...overrides
  };
}
