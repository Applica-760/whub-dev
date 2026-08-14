import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useOperatorTerminals } from "./operatorTerminals";

const response = (data?: unknown, ok = true) => ({
  json: async () => data,
  ok,
  status: ok ? 200 : 500,
  statusText: ok ? "OK" : "Internal Server Error",
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("useOperatorTerminals", () => {
  it("一覧・起動・停止とpendingを管理する", async () => {
    let resolveStart!: (value: ReturnType<typeof response>) => void;
    const startResponse = new Promise<ReturnType<typeof response>>(
      (resolve) => {
        resolveStart = resolve;
      },
    );
    vi.stubGlobal(
      "fetch",
      vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
        if (init?.method === "POST") return startResponse;
        if (init?.method === "DELETE") return Promise.resolve(response());
        return Promise.resolve(
          response({ terminals: [{ operator_id: "one" }] }),
        );
      }),
    );
    const { result } = renderHook(() => useOperatorTerminals());

    await waitFor(() => expect(result.current.loaded).toBe(true));
    expect(result.current.operators).toEqual([{ operator_id: "one" }]);

    let started: ReturnType<typeof result.current.startOperator>;
    act(() => {
      started = result.current.startOperator();
    });
    expect(result.current.pending).toBe(true);
    await act(async () => {
      resolveStart(response({ operator_id: "two" }));
      expect(await started).toEqual({ operator_id: "two" });
    });
    expect(result.current.operators).toEqual([
      { operator_id: "one" },
      { operator_id: "two" },
    ]);

    await act(() => result.current.stopOperator("one"));
    expect(fetch).toHaveBeenCalledWith("/api/operator-terminals/one", {
      method: "DELETE",
    });
    expect(result.current.operators).toEqual([{ operator_id: "two" }]);
    expect(result.current.pending).toBe(false);
  });

  it("APIエラーを表示用文字列へ変換する", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(response({ detail: "Operator unavailable" }, false)),
      ),
    );
    const { result } = renderHook(() => useOperatorTerminals());

    await waitFor(() => expect(result.current.loaded).toBe(true));
    expect(result.current.error).toBe("Operator unavailable");
  });
});
