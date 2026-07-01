import { useEffect, useMemo, useState } from "react";

import type { EntityNode, Position } from "../types/api";

export interface ActiveRunSeed {
  entity: EntityNode | null;
  positionId: string | null;
  runId: string | null;
  status: string;
}

interface StoredRunSeed {
  entity: EntityNode;
  runId: string;
  status: string;
}

export function usePortfolioRunSeeds(
  positions: Position[],
  activeRun: ActiveRunSeed
): Position[] {
  const [seeds, setSeeds] = useState<Record<string, StoredRunSeed>>({});

  useEffect(() => {
    const { entity, positionId, runId, status } = activeRun;
    if (!positionId || !runId || !entity || !isSeedStatus(status)) {
      return;
    }
    setSeeds((current) => {
      const existing = current[positionId];
      if (existing?.runId === runId && existing.entity.id === entity.id) {
        return current;
      }
      return {
        ...current,
        [positionId]: {
          entity,
          runId,
          status
        }
      };
    });
  }, [activeRun.entity, activeRun.positionId, activeRun.runId, activeRun.status]);

  return useMemo(
    () => positions.map((position) => enrichPosition(position, seeds[position.id])),
    [positions, seeds]
  );
}

function enrichPosition(position: Position, seed: StoredRunSeed | undefined): Position {
  if (!seed || position.latest_run_entity) {
    return position;
  }
  return {
    ...position,
    latest_run_entity: seed.entity,
    latest_run_id: seed.runId,
    latest_run_status: seed.status
  };
}

function isSeedStatus(status: string): boolean {
  return status === "awaiting_confirmation" || status === "completed";
}
