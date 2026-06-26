import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode
} from "react";

import type { Evidence } from "../types/api";

export interface EvidenceDrawerContextValue {
  ids: string[];
  isOpen: boolean;
  knownEvidences: Evidence[];
  open: (evidenceIds: string[]) => void;
  close: () => void;
  remember: (evidences: Evidence[]) => void;
}

const EvidenceDrawerContext = createContext<EvidenceDrawerContextValue | null>(
  null
);

export function EvidenceDrawerProvider({
  children
}: {
  children: ReactNode;
}): JSX.Element {
  const [ids, setIds] = useState<string[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [evidenceById, setEvidenceById] = useState<Map<string, Evidence>>(
    () => new Map()
  );

  const open = useCallback((evidenceIds: string[]) => {
    setIds(Array.from(new Set(evidenceIds)));
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIds([]);
    setIsOpen(false);
  }, []);

  const remember = useCallback((evidences: Evidence[]) => {
    setEvidenceById((previous) => {
      let changed = false;
      const next = new Map(previous);
      evidences.forEach((evidence) => {
        if (next.get(evidence.id) !== evidence) {
          next.set(evidence.id, evidence);
          changed = true;
        }
      });
      return changed ? next : previous;
    });
  }, []);

  const knownEvidences = useMemo(
    () => Array.from(evidenceById.values()),
    [evidenceById]
  );

  const value = useMemo(
    () => ({
      close,
      ids,
      isOpen,
      knownEvidences,
      open,
      remember
    }),
    [close, ids, isOpen, knownEvidences, open, remember]
  );

  return (
    <EvidenceDrawerContext.Provider value={value}>
      {children}
    </EvidenceDrawerContext.Provider>
  );
}

export function useEvidenceDrawer(): EvidenceDrawerContextValue {
  const context = useContext(EvidenceDrawerContext);
  if (!context) {
    throw new Error("useEvidenceDrawer must be used within EvidenceDrawerProvider");
  }
  return context;
}
