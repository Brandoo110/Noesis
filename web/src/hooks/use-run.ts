import { useCallback, useEffect, useState } from "react";

import { getRun, startRun } from "../api/client";
import type { EntityNode, RunDetail, RunStatus } from "../types/api";

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
  entity: EntityNode | null;
}

const DEFAULT_POLL_MS = 1000;

export function useRun(options: UseRunOptions = {}): UseRunResult {
  const pollMs = options.pollMs ?? DEFAULT_POLL_MS;
  const [status, setStatus] = useState<RunViewStatus>("idle");
  const [runId, setRunId] = useState<string | null>(null);
  const [thesisId, setThesisId] = useState<string | null>(null);
  const [entityId, setEntityId] = useState<string | null>(null);
  const [entity, setEntity] = useState<EntityNode | null>(null);
  const [pollingRunId, setPollingRunId] = useState<string | null>(null);

  const applyDetail = useCallback((detail: RunDetail): void => {
    setStatus(detail.status as RunStatus);
    setThesisId(detail.thesis_id);
    setEntityId(detail.entity?.id ?? null);
    setEntity(detail.entity);
    if (detail.status !== "running") {
      setPollingRunId(null);
    }
  }, []);

  const pollRun = useCallback(
    async (nextRunId: string): Promise<void> => {
      applyDetail(await getRun(nextRunId));
    },
    [applyDetail]
  );

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
    setEntity(null);
    if (summary.status === "running") {
      setPollingRunId(summary.run_id);
      return;
    }
    setPollingRunId(null);
    await pollRun(summary.run_id);
  }, [pollRun]);

  return {
    start,
    status,
    runId,
    thesisId,
    entityId,
    entity
  };
}
