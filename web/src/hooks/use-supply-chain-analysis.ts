import { useCallback, useMemo, useRef, useState } from "react";

import { expandEntity } from "../api/client";
import type { EntityNode, Position } from "../types/api";

interface ActiveRunSeed {
  positionId: string | null;
  entity: EntityNode | null;
}

export interface SupplyChainSeed {
  positionId: string;
  entityId: string;
}

export interface UseSupplyChainAnalysisOptions {
  activeRun: ActiveRunSeed;
  onAnalyzed?: () => Promise<void> | void;
  positions: Position[];
}

export interface UseSupplyChainAnalysisResult {
  analyze: () => Promise<void>;
  error: string | null;
  isAnalyzing: boolean;
  seedCount: number;
}

export function useSupplyChainAnalysis({
  activeRun,
  onAnalyzed,
  positions
}: UseSupplyChainAnalysisOptions): UseSupplyChainAnalysisResult {
  const expandedKeysRef = useRef(new Set<string>());
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const seeds = useMemo(
    () => supplyChainSeeds(positions, activeRun),
    [activeRun, positions]
  );

  const analyze = useCallback(async (): Promise<void> => {
    setIsAnalyzing(true);
    setError(null);
    try {
      for (const seed of seeds) {
        const key = `${seed.positionId}:${seed.entityId}`;
        if (expandedKeysRef.current.has(key)) {
          continue;
        }
        await expandEntity(seed.entityId, seed.positionId);
        expandedKeysRef.current.add(key);
      }
      await onAnalyzed?.();
    } catch (caught) {
      setError(toErrorMessage(caught));
    } finally {
      setIsAnalyzing(false);
    }
  }, [onAnalyzed, seeds]);

  return {
    analyze,
    error,
    isAnalyzing,
    seedCount: seeds.length
  };
}

function supplyChainSeeds(
  positions: Position[],
  activeRun: ActiveRunSeed
): SupplyChainSeed[] {
  const seeds = new Map<string, SupplyChainSeed>();
  for (const position of positions) {
    if (position.latest_run_entity) {
      seeds.set(position.id, {
        positionId: position.id,
        entityId: position.latest_run_entity.id
      });
    }
  }
  if (activeRun.positionId && activeRun.entity) {
    seeds.set(activeRun.positionId, {
      positionId: activeRun.positionId,
      entityId: activeRun.entity.id
    });
  }
  return Array.from(seeds.values());
}

function toErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "供应链分析失败";
}
