import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as client from "../api/client";
import type { Evidence } from "../types/api";
import { useEvidence } from "./use-evidence";

vi.mock("../api/client", () => ({
  getEvidence: vi.fn()
}));

const getEvidenceMock = vi.mocked(client.getEvidence);

describe("useEvidence", () => {
  it("uses known evidences and fetches only missing ids", async () => {
    getEvidenceMock.mockResolvedValue(makeEvidence("evidence-2"));

    render(
      <Probe
        evidenceIds={["evidence-1", "evidence-2"]}
        knownEvidences={[makeEvidence("evidence-1")]}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("evidence-1,evidence-2")).toBeInTheDocument();
    });
    expect(getEvidenceMock).toHaveBeenCalledTimes(1);
    expect(getEvidenceMock).toHaveBeenCalledWith("evidence-2");
  });

  it("returns per-id errors without dropping loaded evidences", async () => {
    getEvidenceMock.mockRejectedValue(new Error("missing evidence"));

    render(
      <Probe
        evidenceIds={["evidence-1", "missing"]}
        knownEvidences={[makeEvidence("evidence-1")]}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("evidence-1")).toBeInTheDocument();
      expect(screen.getByText("missing:missing evidence")).toBeInTheDocument();
    });
  });
});

interface ProbeProps {
  evidenceIds: string[];
  knownEvidences: Evidence[];
}

function Probe({ evidenceIds, knownEvidences }: ProbeProps): JSX.Element {
  const result = useEvidence(evidenceIds, knownEvidences);
  return (
    <div>
      <p>{result.evidences.map((item) => item.id).join(",")}</p>
      <p>{result.isLoading ? "loading" : "ready"}</p>
      {Object.entries(result.errors).map(([id, message]) => (
        <p key={id}>
          {id}:{message}
        </p>
      ))}
    </div>
  );
}

function makeEvidence(id: string): Evidence {
  return {
    id,
    source: "web",
    source_tier: 2,
    url: `https://example.com/${id}`,
    title: `Title ${id}`,
    snippet: `Snippet ${id}`,
    captured_at: "2026-06-27T00:00:00Z",
    published_at: null
  };
}
