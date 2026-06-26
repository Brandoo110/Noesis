import { useCallback, useEffect, useState } from "react";

import { getNeighbors, getRelevance, getRun } from "../api/client";
import type { Edge, EntityNode, Evidence, IntelItem, RunDetail, Thesis } from "../types/api";

export interface StockDetailData {
  entityId: string;
  positionId: string;
  runId: string;
  run: RunDetail | null;
  entity: EntityNode | null;
  evidences: Evidence[];
  intelItems: IntelItem[];
  thesis: Thesis | null;
  neighbors: Edge[];
  relevancePath: EntityNode[];
}

export interface StockDetailErrors {
  run?: string;
  neighbors?: string;
  relevance?: string;
}

export interface UseStockDetailResult {
  detail: StockDetailData;
  errors: StockDetailErrors;
  isLoading: boolean;
  refresh: () => Promise<void>;
}

type SliceName = keyof StockDetailErrors;

interface SettledSlice<T> {
  data: T | null;
  error?: string;
}

export function useStockDetail(
  entityId: string,
  runId: string,
  positionId: string
): UseStockDetailResult {
  const [detail, setDetail] = useState<StockDetailData>(() =>
    emptyDetail(entityId, runId, positionId)
  );
  const [errors, setErrors] = useState<StockDetailErrors>({});
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    const [runSlice, neighborsSlice, relevanceSlice] = await Promise.all([
      settle("run", getRun(runId)),
      settle("neighbors", getNeighbors(entityId)),
      settle("relevance", getRelevance(entityId, positionId))
    ]);

    setDetail({
      entityId,
      runId,
      positionId,
      run: runSlice.data,
      entity: runSlice.data?.entity ?? null,
      evidences: runSlice.data?.evidences ?? [],
      intelItems: runSlice.data?.intel_items ?? [],
      thesis: runSlice.data?.thesis ?? null,
      neighbors: neighborsSlice.data?.edges ?? [],
      relevancePath: relevanceSlice.data?.path ?? []
    });
    setErrors(
      collectErrors({
        run: runSlice,
        neighbors: neighborsSlice,
        relevance: relevanceSlice
      })
    );
    setIsLoading(false);
  }, [entityId, positionId, runId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { detail, errors, isLoading, refresh };
}

function emptyDetail(
  entityId: string,
  runId: string,
  positionId: string
): StockDetailData {
  return {
    entityId,
    runId,
    positionId,
    run: null,
    entity: null,
    evidences: [],
    intelItems: [],
    thesis: null,
    neighbors: [],
    relevancePath: []
  };
}

async function settle<T>(
  _name: SliceName,
  promise: Promise<T>
): Promise<SettledSlice<T>> {
  try {
    return { data: await promise };
  } catch (caught) {
    return { data: null, error: toErrorMessage(caught) };
  }
}

function collectErrors(slices: {
  run: SettledSlice<unknown>;
  neighbors: SettledSlice<unknown>;
  relevance: SettledSlice<unknown>;
}): StockDetailErrors {
  return Object.fromEntries(
    Object.entries(slices)
      .filter(([, slice]) => slice.error)
      .map(([key, slice]) => [key, slice.error])
  ) as StockDetailErrors;
}

function toErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "请求失败";
}
