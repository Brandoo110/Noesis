import {
  useCallback,
  useState,
  type Dispatch,
  type FormEvent,
  type SetStateAction
} from "react";

import { createPosition, resolvePosition } from "../api/client";
import type { PositionFormState } from "../components/portfolio/PositionInput";
import {
  buildInput,
  toErrorMessage
} from "../components/portfolio/portfolio-home-utils";
import type { CreatePositionInput, ResolvePositionResult } from "../types/api";

export const EMPTY_POSITION_FORM: PositionFormState = {
  symbol: "",
  market: "US",
  name: "",
  kind: "owned"
};

export interface UsePositionEntryOptions {
  onCreated: () => Promise<void> | void;
}

export interface UsePositionEntryResult {
  form: PositionFormState;
  setForm: Dispatch<SetStateAction<PositionFormState>>;
  resolution: ResolvePositionResult | null;
  isBusy: boolean;
  error: string | null;
  submit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  confirm: () => Promise<void>;
  forceCreate: () => Promise<void>;
  cancel: () => void;
}

export function usePositionEntry({
  onCreated
}: UsePositionEntryOptions): UsePositionEntryResult {
  const [form, setForm] = useState<PositionFormState>(EMPTY_POSITION_FORM);
  const [resolution, setResolution] = useState<ResolvePositionResult | null>(
    null
  );
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const finishCreate = useCallback(
    async (input: CreatePositionInput): Promise<void> => {
      setIsBusy(true);
      setError(null);
      try {
        await createPosition(input);
        setResolution(null);
        setForm(EMPTY_POSITION_FORM);
        await onCreated();
      } catch (caught) {
        setError(toErrorMessage(caught));
      } finally {
        setIsBusy(false);
      }
    },
    [onCreated]
  );

  const submit = useCallback(
    async (event: FormEvent<HTMLFormElement>): Promise<void> => {
      event.preventDefault();
      const input = buildInput(form);
      if (!input.symbol && !input.name) {
        setError("请输入 Symbol 或公司名称");
        return;
      }
      setIsBusy(true);
      setError(null);
      try {
        setResolution(await resolvePosition(input));
      } catch (caught) {
        setError(toErrorMessage(caught));
      } finally {
        setIsBusy(false);
      }
    },
    [form]
  );

  const confirm = useCallback(async (): Promise<void> => {
    if (resolution === null || resolution.status !== "resolved") {
      return;
    }
    await finishCreate({
      symbol: resolution.symbol,
      market: resolution.market,
      name: resolution.name,
      kind: form.kind
    });
  }, [finishCreate, form.kind, resolution]);

  const forceCreate = useCallback(async (): Promise<void> => {
    await finishCreate(buildInput(form));
  }, [finishCreate, form]);

  const cancel = useCallback((): void => {
    setResolution(null);
  }, []);

  return {
    form,
    setForm,
    resolution,
    isBusy,
    error,
    submit,
    confirm,
    forceCreate,
    cancel
  };
}
