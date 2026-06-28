import { type FormEvent, useCallback, useEffect, useState } from "react";

import { createPosition, listPositions } from "../../api/client";
import { GraphExplorer } from "../graph/GraphExplorer";
import { useRun } from "../../hooks/use-run";
import type {
  CreatePositionInput,
  EntityNode,
  Position,
  PositionKind
} from "../../types/api";
import { OverlapPanel } from "./OverlapPanel";
import { PortfolioBrief } from "./PortfolioBrief";
import { PositionList } from "./PositionList";

interface PositionFormState {
  symbol: string;
  market: string;
  name: string;
  kind: PositionKind;
}

const EMPTY_FORM: PositionFormState = {
  symbol: "",
  market: "US",
  name: "",
  kind: "owned"
};

export function PortfolioHome(): JSX.Element {
  const [positions, setPositions] = useState<Position[]>([]);
  const [form, setForm] = useState<PositionFormState>(EMPTY_FORM);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [activePositionId, setActivePositionId] = useState<string | null>(null);
  const [graphSeed, setGraphSeed] = useState<GraphSeed | null>(null);
  const [overlapRefreshKey, setOverlapRefreshKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const run = useRun();

  const refreshOverlaps = useCallback((): void => {
    setOverlapRefreshKey((current) => current + 1);
  }, []);

  const refreshPositions = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      setPositions(await listPositions());
    } catch (caught) {
      setError(toErrorMessage(caught));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshPositions();
  }, [refreshPositions]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    try {
      await createPosition(buildInput(form));
      setForm(EMPTY_FORM);
      await refreshPositions();
    } catch (caught) {
      setError(toErrorMessage(caught));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleStartRun(positionId: string): Promise<void> {
    setError(null);
    setActivePositionId(positionId);
    try {
      await run.start(positionId);
      refreshOverlaps();
    } catch (caught) {
      setError(toErrorMessage(caught));
    }
  }

  async function handleThesisConfirmed(): Promise<void> {
    setError(null);
    try {
      await run.refresh();
      refreshOverlaps();
    } catch (caught) {
      setError(toErrorMessage(caught));
    }
  }

  return (
    <section aria-labelledby="portfolio-title">
      <header>
        <h1 id="portfolio-title">Noesis Portfolio</h1>
      </header>

      <form aria-label="新增持仓表单" onSubmit={(event) => void handleSubmit(event)}>
        <label>
          Symbol
          <input
            name="symbol"
            onChange={(event) => setFormField("symbol", event.target.value, setForm)}
            required
            value={form.symbol}
          />
        </label>
        <label>
          Market
          <input
            name="market"
            onChange={(event) => setFormField("market", event.target.value, setForm)}
            required
            value={form.market}
          />
        </label>
        <label>
          Name
          <input
            name="name"
            onChange={(event) => setFormField("name", event.target.value, setForm)}
            value={form.name}
          />
        </label>
        <label>
          Kind
          <select
            name="kind"
            onChange={(event) =>
              setFormField("kind", event.target.value as PositionKind, setForm)
            }
            value={form.kind}
          >
            <option value="owned">owned</option>
            <option value="watching">watching</option>
          </select>
        </label>
        <button disabled={isSaving} type="submit">
          新增持仓
        </button>
      </form>

      {error ? <p role="alert">{error}</p> : null}
      {isLoading ? (
        <p>加载中...</p>
      ) : (
        <PositionList
          activePositionId={activePositionId}
          onViewGraph={(positionId, seedEntity) => {
            if (run.runId && run.positionId === positionId) {
              setGraphSeed({ positionId, runId: run.runId, seedEntity });
            }
          }}
          onStartRun={handleStartRun}
          positions={positions}
          runEntity={run.entity}
          runId={run.runId}
          runPositionId={run.positionId}
          runStatus={run.status}
        />
      )}
      {!isLoading ? (
        <>
          <PortfolioBrief refreshKey={overlapRefreshKey} />
          <OverlapPanel refreshKey={overlapRefreshKey} />
        </>
      ) : null}
      {graphSeed ? (
        <GraphExplorer
          onThesisConfirmed={() => void handleThesisConfirmed()}
          positionId={graphSeed.positionId}
          runId={graphSeed.runId}
          seedEntity={graphSeed.seedEntity}
        />
      ) : null}
    </section>
  );
}

interface GraphSeed {
  positionId: string;
  runId: string;
  seedEntity: EntityNode;
}

function buildInput(form: PositionFormState): CreatePositionInput {
  const name = form.name.trim();
  return {
    symbol: form.symbol.trim(),
    market: form.market.trim(),
    name: name.length > 0 ? name : null,
    kind: form.kind
  };
}

function setFormField<Key extends keyof PositionFormState>(
  key: Key,
  value: PositionFormState[Key],
  setForm: React.Dispatch<React.SetStateAction<PositionFormState>>
): void {
  setForm((current) => ({ ...current, [key]: value }));
}

function toErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "请求失败";
}
