import { type FormEvent, useCallback, useEffect, useState } from "react";

import { createPosition, listPositions } from "../../api/client";
import { useRun } from "../../hooks/use-run";
import type { CreatePositionInput, Position, PositionKind } from "../../types/api";

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
  const [error, setError] = useState<string | null>(null);
  const run = useRun();

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
          onStartRun={handleStartRun}
          positions={positions}
          runId={run.runId}
          runStatus={run.status}
        />
      )}
    </section>
  );
}

interface PositionListProps {
  activePositionId: string | null;
  onStartRun: (positionId: string) => Promise<void>;
  positions: Position[];
  runId: string | null;
  runStatus: string;
}

function PositionList({
  activePositionId,
  onStartRun,
  positions,
  runId,
  runStatus
}: PositionListProps): JSX.Element {
  if (positions.length === 0) {
    return <p>暂无持仓</p>;
  }

  return (
    <ul aria-label="持仓列表">
      {positions.map((position) => (
        <li key={position.id}>
          <strong>{position.symbol}</strong>
          <span>{position.name ?? "未命名"}</span>
          <span>{position.market}</span>
          <span>{position.kind}</span>
          <button
            aria-label={`开始研究 ${position.symbol}`}
            onClick={() => void onStartRun(position.id)}
            type="button"
          >
            开始研究
          </button>
          {activePositionId === position.id ? (
            <span aria-label={`研究状态 ${position.symbol}`}>
              <span>{runStatus}</span>
              {runId ? <span>{runId}</span> : null}
            </span>
          ) : null}
        </li>
      ))}
    </ul>
  );
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
