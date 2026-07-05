import { describe, expect, it } from "vitest";
import type { Edge as FlowEdge, Node as FlowNode } from "reactflow";

import type { Edge, EntityNode } from "../../types/api";
import type { EdgeViewData } from "./EdgeView";
import type { EntityNodeViewData } from "./EntityNodeView";
import { buildGraphRenderModel } from "./graph-render-model";

describe("buildGraphRenderModel", () => {
  it("places lazy-expanded children to the right of their parent", () => {
    const seed = makeEntity({ id: "entity-nvda", name: "NVIDIA Corp", symbol: "NVDA" });
    const micron = makeEntity({ id: "entity-mu", name: "Micron", symbol: "MU" });
    const hynix = makeEntity({
      id: "entity-hynix",
      name: "SK Hynix",
      symbol: "000660.KS"
    });
    const aiChips = makeEntity({
      id: "segment-ai-chips",
      name: "AI Chips",
      node_type: "segment",
      symbol: null
    });

    const model = buildGraphRenderModel(
      seed,
      [
        makeNode(seed, true),
        makeNode(micron, false, true),
        makeNode(hynix),
        makeNode(aiChips)
      ],
      [
        makeFlowEdge("edge-nvda-mu", seed.id, micron, "supplier"),
        makeFlowEdge("edge-mu-hynix", micron.id, hynix, "supplier"),
        makeFlowEdge("edge-mu-ai-chips", micron.id, aiChips, "belongs_to")
      ],
      "all"
    );

    const seedNode = findNode(model, seed.id);
    const micronNode = findNode(model, micron.id);
    const hynixNode = findNode(model, hynix.id);
    const aiChipsNode = findNode(model, aiChips.id);

    expect(micronNode.x).toBeGreaterThan(seedNode.x);
    expect(hynixNode.x).toBeGreaterThan(micronNode.x);
    expect(aiChipsNode.x).toBeGreaterThan(micronNode.x);
  });

  it("grows the stage vertically instead of relying on an inner scrollbar", () => {
    const seed = makeEntity({ id: "entity-nvda", name: "NVIDIA Corp", symbol: "NVDA" });
    const neighbors = Array.from({ length: 9 }, (_, index) =>
      makeEntity({
        id: `entity-peer-${index}`,
        name: `Peer ${index}`,
        symbol: `P${index}`
      })
    );

    const model = buildGraphRenderModel(
      seed,
      [makeNode(seed, true), ...neighbors.map((neighbor) => makeNode(neighbor))],
      neighbors.map((neighbor, index) =>
        makeFlowEdge(`edge-peer-${index}`, seed.id, neighbor, "competitor")
      ),
      "all"
    );

    expect(model.height).toBeGreaterThan(560);
  });

  it("keeps a focused node visible when filters hide its adjacent edges", () => {
    const seed = makeEntity({ id: "entity-nvda", name: "NVIDIA Corp", symbol: "NVDA" });
    const amd = makeEntity({ id: "entity-amd", name: "AMD", symbol: "AMD" });

    const model = buildGraphRenderModel(
      seed,
      [makeNode(seed, true), makeNode(amd)],
      [makeFlowEdge("edge-nvda-amd", seed.id, amd, "competitor")],
      {
        basisFilter: "all",
        focusedEntityId: amd.id,
        relationFilter: "supplier"
      }
    );

    expect(findNode(model, seed.id)).toBeDefined();
    expect(findNode(model, amd.id)).toBeDefined();
    expect(model.edges).toHaveLength(0);
  });
});

function findNode(
  model: ReturnType<typeof buildGraphRenderModel>,
  id: string
): ReturnType<typeof buildGraphRenderModel>["nodes"][number] {
  const node = model.nodes.find((candidate) => candidate.id === id);
  expect(node).toBeDefined();
  return node as ReturnType<typeof buildGraphRenderModel>["nodes"][number];
}

function makeFlowEdge(
  id: string,
  source: string,
  neighbor: EntityNode,
  relation: Edge["relation"]
): FlowEdge<EdgeViewData> {
  return {
    id,
    source,
    target: neighbor.id,
    type: "edge",
    data: { edge: makeEdge(id, neighbor, relation) }
  };
}

function makeNode(
  entity: EntityNode,
  isSeed = false,
  expanded = false
): FlowNode<EntityNodeViewData> {
  return {
    id: entity.id,
    position: { x: 0, y: 0 },
    type: "entity",
    data: {
      entity,
      expanded,
      isSeed,
      onExpand: () => undefined
    }
  };
}

function makeEdge(
  id: string,
  neighbor: EntityNode,
  relation: Edge["relation"]
): Edge {
  return {
    id,
    to_entity_id: neighbor.id,
    to_name: neighbor.name,
    to_symbol: neighbor.symbol,
    relation,
    basis: "source_backed",
    confidence: 0.82,
    evidence_ids: ["evidence-1"],
    source_tier: 2,
    rationale: "Source-backed relation.",
    neighbor
  };
}

function makeEntity(overrides: Partial<EntityNode> = {}): EntityNode {
  return {
    id: "entity-nvda",
    name: "NVIDIA Corp",
    node_type: "company",
    symbol: "NVDA",
    market: "US",
    ...overrides
  };
}
