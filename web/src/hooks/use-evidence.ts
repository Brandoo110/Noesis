import { useEffect, useMemo, useState } from "react";

import { getEvidence } from "../api/client";
import type { Evidence } from "../types/api";

export interface UseEvidenceResult {
  evidences: Evidence[];
  isLoading: boolean;
  errors: Record<string, string>;
}

type EvidenceFetchResult =
  | { kind: "success"; id: string; evidence: Evidence }
  | { kind: "error"; id: string; error: string };

export function useEvidence(
  evidenceIds: string[],
  knownEvidences: Evidence[]
): UseEvidenceResult {
  const uniqueIds = useMemo(
    () => Array.from(new Set(evidenceIds)),
    [evidenceIds]
  );
  const knownById = useMemo(
    () => new Map(knownEvidences.map((evidence) => [evidence.id, evidence])),
    [knownEvidences]
  );
  const [fetchedById, setFetchedById] = useState<Map<string, Evidence>>(
    () => new Map()
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);

  const missingIds = useMemo(
    () =>
      uniqueIds.filter(
        (id) => !knownById.has(id) && !fetchedById.has(id) && !errors[id]
      ),
    [errors, fetchedById, knownById, uniqueIds]
  );

  useEffect(() => {
    if (missingIds.length === 0) {
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    void Promise.all(
      missingIds.map(async (id): Promise<EvidenceFetchResult> => {
        try {
          return { evidence: await getEvidence(id), id, kind: "success" };
        } catch (error) {
          return { error: errorMessage(error), id, kind: "error" };
        }
      })
    ).then((results) => {
      if (cancelled) {
        return;
      }
      setFetchedById((previous) => {
        const next = new Map(previous);
        results.forEach((result) => {
          if (result.kind === "success") {
            next.set(result.id, result.evidence);
          }
        });
        return next;
      });
      setErrors((previous) => {
        const next = { ...previous };
        results.forEach((result) => {
          if (result.kind === "error") {
            next[result.id] = result.error;
          } else {
            delete next[result.id];
          }
        });
        return next;
      });
      setIsLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [missingIds]);

  const evidences = useMemo(
    () =>
      uniqueIds.flatMap((id) => {
        const evidence = knownById.get(id) ?? fetchedById.get(id);
        return evidence ? [evidence] : [];
      }),
    [fetchedById, knownById, uniqueIds]
  );

  const activeErrors = useMemo(() => {
    const next: Record<string, string> = {};
    uniqueIds.forEach((id) => {
      if (errors[id]) {
        next[id] = errors[id];
      }
    });
    return next;
  }, [errors, uniqueIds]);

  return { errors: activeErrors, evidences, isLoading };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "unknown error";
}
