import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { REDLINE_PATTERN } from "./test/redline";

interface DownloadCapture {
  anchor: HTMLAnchorElement;
  blobs: Blob[];
  restore: () => void;
}

describe("App redesign markdown export", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("exports the stock report markdown from the detail drawer", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "查看图谱 NVDA" }));
    fireEvent.click(screen.getByRole("button", { name: "个股详情" }));
    const capture = installDownloadCapture();
    fireEvent.click(
      within(screen.getByRole("dialog", { name: "个股详情" })).getByRole("button", {
        name: "导出报告 Markdown"
      })
    );

    const markdown = await readBlobText(capture.blobs[0]);
    expect(capture.anchor.download).toBe("nvda-report.md");
    expect(capture.anchor.click).toHaveBeenCalledTimes(1);
    expect(markdown).toContain("# NVDA 深度报告");
    expect(markdown).toContain("## 摘要");
    expect(markdown).toContain("## Thesis");
    expect(markdown).toContain("## 来源清单");
    expect(markdown).toContain("https://example.com/ev-101");
    expect(markdown).not.toMatch(REDLINE_PATTERN);
    capture.restore();
  });

  it("exports the portfolio brief markdown from the home view", async () => {
    render(<App />);

    const capture = installDownloadCapture();
    fireEvent.click(
      within(screen.getByLabelText("组合 Brief")).getByRole("button", {
        name: "导出 Markdown"
      })
    );

    const markdown = await readBlobText(capture.blobs[0]);
    expect(capture.anchor.download).toBe("portfolio-brief.md");
    expect(capture.anchor.click).toHaveBeenCalledTimes(1);
    expect(markdown).toContain("# 组合 Brief");
    expect(markdown).toContain("AI 加速计算");
    expect(markdown).toContain("基于推断");
    expect(markdown).not.toMatch(REDLINE_PATTERN);
    capture.restore();
  });
});

function installDownloadCapture(): DownloadCapture {
  const blobs: Blob[] = [];
  const anchor = document.createElement("a");
  vi.spyOn(anchor, "click").mockImplementation(() => undefined);
  const previousCreateObjectURL = URL.createObjectURL;
  const previousRevokeObjectURL = URL.revokeObjectURL;
  URL.createObjectURL = vi.fn((blob: Blob) => {
    blobs.push(blob);
    return "blob:report";
  });
  URL.revokeObjectURL = vi.fn();
  const originalCreateElement = document.createElement.bind(document);
  const createElement = vi.spyOn(document, "createElement");
  createElement.mockImplementation(((tagName: string, options?: ElementCreationOptions) => {
    if (tagName.toLowerCase() === "a") {
      return anchor;
    }
    return originalCreateElement(tagName, options);
  }) as typeof document.createElement);
  return {
    anchor,
    blobs,
    restore: () => {
      createElement.mockRestore();
      URL.createObjectURL = previousCreateObjectURL;
      URL.revokeObjectURL = previousRevokeObjectURL;
    }
  };
}

function readBlobText(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}
