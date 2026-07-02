import type { Dispatch, FormEvent, SetStateAction } from "react";

import type { PositionKind } from "../../types/api";

export interface PositionFormState {
  symbol: string;
  market: string;
  name: string;
  kind: PositionKind;
}

interface PositionInputProps {
  form: PositionFormState;
  isSaving: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  setForm: Dispatch<SetStateAction<PositionFormState>>;
}

export function PositionInput({
  form,
  isSaving,
  onSubmit,
  setForm
}: PositionInputProps): JSX.Element {
  return (
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
  );
}

function setFormField<Key extends keyof PositionFormState>(
  key: Key,
  value: PositionFormState[Key],
  setForm: Dispatch<SetStateAction<PositionFormState>>
): void {
  setForm((current) => ({ ...current, [key]: value }));
}
