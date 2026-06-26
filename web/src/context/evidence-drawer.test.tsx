import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  EvidenceDrawerProvider,
  useEvidenceDrawer
} from "./evidence-drawer";

describe("EvidenceDrawerProvider", () => {
  it("opens and closes a global evidence drawer state", () => {
    render(
      <EvidenceDrawerProvider>
        <Probe />
      </EvidenceDrawerProvider>
    );

    expect(screen.getByText("closed:")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "open evidence" }));
    expect(screen.getByText("open:evidence-1,evidence-2")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "close evidence" }));
    expect(screen.getByText("closed:")).toBeInTheDocument();
  });
});

function Probe(): JSX.Element {
  const drawer = useEvidenceDrawer();
  return (
    <div>
      <p>
        {drawer.isOpen ? "open" : "closed"}:{drawer.ids.join(",")}
      </p>
      <button
        onClick={() => drawer.open(["evidence-1", "evidence-2"])}
        type="button"
      >
        open evidence
      </button>
      <button onClick={drawer.close} type="button">
        close evidence
      </button>
    </div>
  );
}
