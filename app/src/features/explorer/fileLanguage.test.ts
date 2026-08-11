import { describe, expect, it } from "vitest";

import { fileLanguage, highlightLine } from "./fileLanguage";

describe("fileLanguage", () => {
  it("拡張子から構文ハイライト言語を選ぶ", () => {
    expect(fileLanguage("src/App.tsx")).toBe("typescript");
    expect(highlightLine("const value = 1", "src/App.ts")).toContain(
      "hljs-keyword",
    );
  });
});
