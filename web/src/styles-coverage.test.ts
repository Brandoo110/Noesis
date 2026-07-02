import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

const SRC_ROOT = path.resolve(__dirname);
const CLASS_NAME_PATTERN = /className=(?:\"([^\"]+)\"|'([^']+)'|{`([^`]+)`}|{\"([^\"]+)\"}|{'([^']+)'})/g;
const CSS_CLASS_PATTERN = /\.(-?[_a-zA-Z]+[_a-zA-Z0-9-]*)\b/g;
const IGNORED_CLASS_PARTS = new Set(["${className ?? \"\"}", "${className ?? ''}"]);

describe("stylesheet coverage", () => {
  it("defines every static className used by source components", () => {
    const usedClasses = collectUsedClasses();
    const definedClasses = collectDefinedClasses();
    const missingClasses = [...usedClasses]
      .filter((className) => !definedClasses.has(className))
      .sort();

    expect(missingClasses).toEqual([]);
  });
});

function collectUsedClasses(): Set<string> {
  const classes = new Set<string>();
  for (const filePath of walk(SRC_ROOT)) {
    if (!filePath.endsWith(".tsx") || isTestFile(filePath)) {
      continue;
    }
    const content = fs.readFileSync(filePath, "utf8");
    for (const match of content.matchAll(CLASS_NAME_PATTERN)) {
      const raw = match[1] ?? match[2] ?? match[3] ?? match[4] ?? match[5] ?? "";
      for (const className of raw.split(/\s+/)) {
        if (className && !IGNORED_CLASS_PARTS.has(className) && !className.startsWith("${")) {
          classes.add(className);
        }
      }
    }
  }
  return classes;
}

function collectDefinedClasses(): Set<string> {
  const classes = new Set<string>();
  for (const filePath of walk(SRC_ROOT)) {
    if (filePath.endsWith(".css")) {
      const content = fs.readFileSync(filePath, "utf8");
      for (const match of content.matchAll(CSS_CLASS_PATTERN)) {
        classes.add(match[1]);
      }
    }
  }
  return classes;
}

function isTestFile(filePath: string): boolean {
  return (
    filePath.endsWith(".test.tsx") ||
    filePath.endsWith(".test.ts") ||
    filePath.includes(`${path.sep}test${path.sep}`)
  );
}

function walk(dirPath: string): string[] {
  const paths: string[] = [];
  for (const entry of fs.readdirSync(dirPath, { withFileTypes: true })) {
    const entryPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      paths.push(...walk(entryPath));
    } else {
      paths.push(entryPath);
    }
  }
  return paths;
}
