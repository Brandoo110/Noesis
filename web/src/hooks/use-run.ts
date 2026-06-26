import { useCallback, useEffect, useState } from "react";

import { getRun, startRun } from "../api/client";
import type { RunStatus } from "../types/api";

type RunViewStatus = "idle" | RunStatus;

export interface UseRunOptions {
  pollMs?: number;
}

export interface UseRunResult {
  start: (positionId: string) => Promise<void>;
  status: RunViewStatus;
  runId: string | null;
  thesisId: string | null;
  entityId: string | null;
}

const DEFAULT_POLL_MS = 1000;

export function useRun(options: UseRunOptions = {}): UseRunResult {
  const pollMs = options.pollMs ?? DEFAULT_POLL_MS;
  const [status, setStatus] = useState<RunViewStatus>("idle");
  const [runId, setRunId] = useState<string | null>(null);
  const [thesisId, setThesisId] = useState<string | null>(null);
  const [entityId, setEntityId] = useState<string | null>(null);
  const [pollingRunId, setPollingRunId] = useState<string | null>(null);

  const pollRun = useCallback(async (nextRunId: string): Promise<void> => {
    const detail = await getRun(nextRunId);
    setStatus(detail.status as RunStatus);
    setThesisId(detail.thesis_id);
    setEntityId(detail.entity?.id ?? null);
    if (detail.status !== "running") {
      setPollingRunId(null);
    }
  }, []);

  useEffect(() => {
    if (!pollingRunId) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      void pollRun(pollingRunId);
    }, pollMs);

    return () => window.clearInterval(intervalId);
  }, [pollingRunId, pollMs, pollRun]);

  const start = useCallback(async (positionId: string): Promise<void> => {
    const summary = await startRun(positionId);
    setRunId(summary.run_id);
    setStatus(summary.status);
    setThesisId(summary.thesis_id);
    setEntityId(null);
    setPollingRunId(summary.status === "running" ? summary.run_id : null);
  }, []);

  return {
    start,
    status,
    runId,
    thesisId,
    entityId
  };
}
