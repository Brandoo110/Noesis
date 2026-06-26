import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../../api/client";
import {
  EvidenceDrawerProvider,
  useEvidenceDrawer
} from "../../context/evidence-drawer";
import type { Evidence } from "../../types/api";
import { EvidenceDrawer } from "./EvidenceDrawer";

vi.mock("../../api/client", () => ({
  getEvidence: vi.fn()
}));

const getEvidenceMock = vi.mocked(client.getEvidence);

describe("EvidenceDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("opens by ids and renders compliant evidence fields", async () => {
    getEvidenceMock.mockResolvedValue(makeEvidence("evidence-1"));

    render(
      <EvidenceDrawerProvider>
        <OpenButton ids={["evidence-1"]} />
        <EvidenceDrawer />
      </EvidenceDrawerProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "open drawer" }));

    expect(
      await screen.findByRole("dialog", { name: "证据抽屉" })
    ).toBeInTheDocument();
    expect(screen.getByText("Title evidence-1")).toBeInTheDocument();
    expect(screen.getByText("Snippet evidence-1")).toBeInTheDocument();
    expect(screen.getByText("tier 2")).toBeInTheDocument();
    expect(screen.getByText("2026-06-27T00:00:00Z")).toBeInTheDocument();
    expect(screen.queryByText("Full article body")).not.toBeInTheDocument();

    const link = screen.getByRole("link", { name: "打开来源" });
    expect(link).toHaveAttribute("href", "https://example.com/evidence-1");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noreferrer");
  });

  it("uses cached known evidence before fetching missing ids", async () => {
    getEvidenceMock.mockResolvedValue(makeEvidence("evidence-2"));

    render(
      <EvidenceDrawerProvider>
        <RememberKnown evidence={makeEvidence("evidence-1")} />
        <OpenButton ids={["evidence-1", "evidence-2"]} />
        <EvidenceDrawer />
      </EvidenceDrawerProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "open drawer" }));

    await waitFor(() => {
      expect(screen.getByText("Title evidence-1")).toBeInTheDocument();
      expect(screen.getByText("Title evidence-2")).toBeInTheDocument();
    });
    expect(getEvidenceMock).toHaveBeenCalledTimes(1);
    expect(getEvidenceMock).toHaveBeenCalledWith("evidence-2");
  });

  it("shows a local error when an evidence fetch fails", async () => {
    getEvidenceMock.mockRejectedValue(new Error("GET /evidences/missing failed: 404"));

    render(
      <EvidenceDrawerProvider>
        <OpenButton ids={["missing"]} />
        <EvidenceDrawer />
      </EvidenceDrawerProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "open drawer" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "missing:GET /evidences/missing failed: 404"
    );
  });
});

function OpenButton({ ids }: { ids: string[] }): JSX.Element {
  const drawer = useEvidenceDrawer();
  return (
    <button onClick={() => drawer.open(ids)} type="button">
      open drawer
    </button>
  );
}

function RememberKnown({ evidence }: { evidence: Evidence }): null {
  const drawer = useEvidenceDrawer();
  useEffect(() => {
    drawer.remember([evidence]);
  }, [drawer, evidence]);
  return null;
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
