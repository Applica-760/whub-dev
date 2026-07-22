import { MantineProvider } from "@mantine/core";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { KnowledgeResponse } from "../../api/client";
import { KnowledgePage } from "./KnowledgePage";
import { KnowledgeWidget } from "./KnowledgeWidget";

const KNOWLEDGE = {
  schema_version: 4,
  definitions: {
    whub: { name: "whub", definition: "projectを統合管理するCLI" },
  },
  relations: [
    { subject: "def:whub", predicate: "manages", object: "def:whub" },
  ],
  policies: {
    knowledge_is_ssot: { statement: "Knowledge YAMLをSSOTとする" },
  },
  constraints: {
    reject_unknown_fields: { statement: "未知フィールドを拒否する" },
  },
  exceptions: {},
} satisfies KnowledgeResponse;

beforeEach(() => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 404 ? "Not Found" : "Server Error",
    json: async () => body,
  } as Response;
}

function renderInMantine(component: React.ReactNode) {
  return render(<MantineProvider env="test">{component}</MantineProvider>);
}

describe("KnowledgeWidget", () => {
  it("分類タブと検索で表示を絞り込む", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(KNOWLEDGE)));
    renderInMantine(<KnowledgeWidget project="whub-dev" />);

    await screen.findAllByText("def:whub");
    fireEvent.click(screen.getByRole("tab", { name: "CON" }));
    expect(screen.getByText("con:reject_unknown_fields")).toBeTruthy();
    expect(screen.queryByText("def:whub")).toBeNull();

    fireEvent.click(screen.getByRole("tab", { name: "All" }));
    fireEvent.change(screen.getByLabelText("Knowledgeを検索"), {
      target: { value: "pol:knowledge_is_ssot" },
    });
    expect(screen.getByText("pol:knowledge_is_ssot")).toBeTruthy();
    expect(screen.queryByText("con:reject_unknown_fields")).toBeNull();

    fireEvent.change(screen.getByLabelText("Knowledgeを検索"), {
      target: { value: "not-found" },
    });
    expect(screen.getByText("該当するKnowledgeはありません")).toBeTruthy();
  });

  it.each([
    [404, "Knowledgeはありません"],
    [500, "Knowledgeを取得できませんでした"],
  ])("取得失敗status %sを区別して表示する", async (status, expected) => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(response({ detail: "request failed" }, status)),
    );
    renderInMantine(<KnowledgeWidget project="whub-dev" />);

    expect(await screen.findByText(expected)).toBeTruthy();
  });
});

describe("KnowledgePage", () => {
  it("whub-devを初期選択し、project切替で再取得する", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/projects") {
        return Promise.resolve(response({ projects: ["local", "whub-dev"] }));
      }
      return Promise.resolve(response(KNOWLEDGE));
    });
    vi.stubGlobal("fetch", fetchMock);
    renderInMantine(<KnowledgePage />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/knowledge/whub-dev",
        undefined,
      );
    });
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/knowledge/local", undefined);
    });
  });
});
