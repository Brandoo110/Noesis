import type { Dispatch, FormEvent, SetStateAction } from "react";

import type { PositionKind, ResolvePositionResult } from "../../types/api";

export interface PositionFormState {
  symbol: string;
  market: string;
  name: string;
  kind: PositionKind;
}

interface PositionInputProps {
  form: PositionFormState;
  isSaving: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  onForceCreate: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  resolution: ResolvePositionResult | null;
  setForm: Dispatch<SetStateAction<PositionFormState>>;
}

export function PositionInput({
  form,
  isSaving,
  onCancel,
  onConfirm,
  onForceCreate,
  onSubmit,
  resolution,
  setForm
}: PositionInputProps): JSX.Element {
  return (
    <>
      <form
        aria-label="新增持仓表单"
        className="add-form"
        onSubmit={onSubmit}
      >
        <label>
          Symbol
          <input
            name="symbol"
            onChange={(event) => setFormField("symbol", event.target.value, setForm)}
            placeholder="可选：TSLA"
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
            placeholder="公司名：SpaceX"
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
        <button className="primary-button" disabled={isSaving} type="submit">
          新增持仓
        </button>
      </form>
      {resolution ? (
        <ResolutionBar
          isSaving={isSaving}
          onCancel={onCancel}
          onConfirm={onConfirm}
          onForceCreate={onForceCreate}
          resolution={resolution}
        />
      ) : null}
    </>
  );
}

interface ResolutionBarProps {
  isSaving: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  onForceCreate: () => void;
  resolution: ResolvePositionResult;
}

function ResolutionBar({
  isSaving,
  onCancel,
  onConfirm,
  onForceCreate,
  resolution
}: ResolutionBarProps): JSX.Element {
  if (resolution.status === "unresolved") {
    return (
      <div aria-label="录入确认" className="compact-alert" role="status">
        <span>未能识别，请补充公司全名或股票代码。</span>
        <button disabled={isSaving} onClick={onForceCreate} type="button">
          仍按原样添加
        </button>
        <button disabled={isSaving} onClick={onCancel} type="button">
          取消
        </button>
      </div>
    );
  }
  if (resolution.existing_position_id !== null) {
    return (
      <div aria-label="录入确认" className="compact-alert" role="status">
        <span>已在组合中：{resolution.existing_position_label}</span>
        <button onClick={onCancel} type="button">
          知道了
        </button>
      </div>
    );
  }
  return (
    <div aria-label="录入确认" className="compact-alert" role="status">
      <span>
        识别为：{resolution.name}（{resolutionMarketLabel(resolution)}）
      </span>
      <button
        className="primary-button"
        disabled={isSaving}
        onClick={onConfirm}
        type="button"
      >
        确认添加
      </button>
      <button disabled={isSaving} onClick={onCancel} type="button">
        取消
      </button>
    </div>
  );
}

function resolutionMarketLabel(resolution: ResolvePositionResult): string {
  if (resolution.symbol) {
    return `${resolution.symbol} · ${resolution.market}`;
  }
  return `${resolution.market} · 无公开代码`;
}

function setFormField<Key extends keyof PositionFormState>(
  key: Key,
  value: PositionFormState[Key],
  setForm: Dispatch<SetStateAction<PositionFormState>>
): void {
  setForm((current) => ({ ...current, [key]: value }));
}
