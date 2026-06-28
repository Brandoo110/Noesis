import { useCallback, useEffect, useRef, useState } from "react";

import { getRun, startRun } from "../api/client";
import type { EntityNode, RunDetail, RunStatus, RunSummary } from "../types/api";

type RunViewStatus = "idle" | RunStatus;

export interface UseRunOptions {
  pollMs?: number;
}

export interface UseRunResult {
  start: (positionId: string) => Promise<void>;
  refresh: () => Promise<void>;
  status: RunViewStatus;
  runId: string | null;
  positionId: string | null;
  thesisId: string | null;
  entityId: string | null;
  entity: EntityNode | null;
}

const DEFAULT_POLL_MS = 1000;

export function useRun(options: UseRunOptions = {}): UseRunResult {
  const pollMs = options.pollMs ?? DEFAULT_POLL_MS;
  const [status, setStatus] = useState<RunViewStatus>("idle");
  const [runId, setRunId] = useState<string | null>(null);
  const [positionId, setPositionId] = useState<string | null>(null);
  const [thesisId, setThesisId] = useState<string | null>(null);
  const [entityId, setEntityId] = useState<string | null>(null);
  const [entity, setEntity] = useState<EntityNode | null>(null);
  const [pollingRunId, setPollingRunId] = useState<string | null>(null);
  const startRequestIdRef = useRef(0);

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

  const start = useCallback(async (nextPositionId: string): Promise<void> => {
    const requestId = startRequestIdRef.current + 1;
    startRequestIdRef.current = requestId;
    setPositionId(nextPositionId);
    setRunId(null);
    setThesisId(null);
    setEntityId(null);
    setEntity(null);
    setPollingRunId(null);
    setStatus("running");
    let summary: RunSummary;
    try {
      summary = await startRun(nextPositionId);
    } catch (caught) {
      if (requestId === startRequestIdRef.current) {
        setStatus("failed");
      }
      throw caught;
    }
    if (requestId !== startRequestIdRef.current) {
      return;
    }
    setRunId(summary.run_id);
    setStatus(summary.status);
    setThesisId(summary.thesis_id);
    if (summary.status === "running") {
      setPollingRunId(summary.run_id);
      return;
    }
    setPollingRunId(null);
    const detail = await getRun(summary.run_id);
    if (requestId === startRequestIdRef.current) {
      applyDetail(detail);
    }
  }, [applyDetail]);

  const refresh = useCallback(async (): Promise<void> => {
    if (!runId) {
      return;
    }
    await pollRun(runId);
  }, [pollRun, runId]);

  return {
    start,
    refresh,
    status,
    runId,
    positionId,
    thesisId,
    entityId,
    entity
  };
}
