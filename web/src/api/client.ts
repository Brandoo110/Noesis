import type {
  ConfirmationInput,
  CreatePositionInput,
  Edge,
  EntityNode,
  Evidence,
  ExpandResult,
  Position,
  Relevance,
  RunDetail,
  RunSummary
} from "../types/api";

interface NeighborsResponse {
  entity_id: string;
  edges: Edge[];
}

interface RepresentativesResponse {
  segment_id: string;
  representatives: Array<{
    id: string;
    name: string;
    symbol: string | null;
  }>;
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export function createPosition(input: CreatePositionInput): Promise<Position> {
  return request<Position>("/positions", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function listPositions(): Promise<Position[]> {
  return request<Position[]>("/positions");
}

export function startRun(positionId: string): Promise<RunSummary> {
  return request<RunSummary>("/runs", {
    method: "POST",
    body: JSON.stringify({ position_id: positionId })
  });
}

export function getRun(runId: string): Promise<RunDetail> {
  return request<RunDetail>(`/runs/${encodeURIComponent(runId)}`);
}

export function confirmThesis(
  thesisId: string,
  confirmation: ConfirmationInput
): Promise<RunSummary> {
  return request<RunSummary>(`/theses/${encodeURIComponent(thesisId)}/confirm`, {
    method: "POST",
    body: JSON.stringify(confirmation)
  });
}

export function expandEntity(
  entityId: string,
  positionId: string
): Promise<ExpandResult> {
  return request<ExpandResult>(`/entities/${encodeURIComponent(entityId)}/expand`, {
    method: "POST",
    body: JSON.stringify({ position_id: positionId })
  });
}

export function getNeighbors(entityId: string): Promise<NeighborsResponse> {
  return request<NeighborsResponse>(`/entities/${encodeURIComponent(entityId)}/neighbors`);
}

export function getRelevance(
  entityId: string,
  positionId: string
): Promise<Relevance> {
  const params = new URLSearchParams({ position_id: positionId });
  return request<Relevance>(
    `/entities/${encodeURIComponent(entityId)}/relevance?${params.toString()}`
  );
}

export async function getRepresentatives(segmentId: string): Promise<EntityNode[]> {
  const response = await request<RepresentativesResponse>(
    `/segments/${encodeURIComponent(segmentId)}/representatives`
  );
  return response.representatives.map((item) => ({
    id: item.id,
    name: item.name,
    node_type: "company",
    symbol: item.symbol,
    market: null
  }));
}

export function getEvidence(id: string): Promise<Evidence> {
  return request<Evidence>(`/evidences/${encodeURIComponent(id)}`);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...JSON_HEADERS,
      ...init.headers
    }
  });
  if (!response.ok) {
    const method = init.method ?? "GET";
    throw new Error(`${method} ${path} failed: ${response.status}`);
  }
  return (await response.json()) as T;
}
