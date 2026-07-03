import type { CreatePositionInput, Position } from "../../types/api";
import type { GraphSeed } from "../views/view-types";
import type { PositionFormState } from "./PositionInput";
import type { PortfolioFilters } from "./PortfolioTopbar";

interface ActiveRunFilter {
  activeRunId: string | null;
  activeRunPositionId: string | null;
}

export function buildInput(form: PositionFormState): CreatePositionInput {
  const symbol = form.symbol.trim();
  const name = form.name.trim();
  return {
    symbol: symbol.length > 0 ? symbol : null,
    market: form.market.trim(),
    name: name.length > 0 ? name : null,
    kind: form.kind
  };
}

export function toErrorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "请求失败";
}

export function prefersReducedMotion(): boolean {
  return (
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function matchesSearch(position: Position, searchQuery: string): boolean {
  const query = searchQuery.trim().toLowerCase();
  if (query.length === 0) {
    return true;
  }

  return [position.symbol, position.name, position.market, position.kind]
    .filter(Boolean)
    .some((value) => value?.toLowerCase().includes(query));
}

export function matchesKind(
  position: Position,
  filter: PortfolioFilters["kind"]
): boolean {
  return filter === "all" || position.kind === filter;
}

export function matchesResearch(
  position: Position,
  filter: PortfolioFilters["research"],
  activeRun: ActiveRunFilter
): boolean {
  if (filter === "all") {
    return true;
  }

  const hasResearch =
    typeof position.latest_run_id === "string" ||
    (activeRun.activeRunPositionId === position.id && activeRun.activeRunId !== null);
  return filter === "researched" ? hasResearch : !hasResearch;
}

export function graphSeedForPosition(
  positions: Position[],
  positionId: string
): GraphSeed | null {
  const position = positions.find((item) => item.id === positionId);
  if (
    !position ||
    !position.latest_run_id ||
    !position.latest_run_entity ||
    !isGraphReadyStatus(position.latest_run_status)
  ) {
    return null;
  }
  return {
    positionId,
    runId: position.latest_run_id,
    seedEntity: position.latest_run_entity
  };
}

function isGraphReadyStatus(status: string | null | undefined): boolean {
  return status === "awaiting_confirmation" || status === "completed";
}
