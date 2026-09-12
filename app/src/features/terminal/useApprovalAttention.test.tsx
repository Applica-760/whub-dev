import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useApprovalAttention } from "./useApprovalAttention";
import type { ApprovalAttention } from "./attentionApi";

let attention: ApprovalAttention[];

class FakeWebSocket {
  static connections: FakeWebSocket[] = [];

  onclose: (() => void) | null = null;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;

  constructor() {
    FakeWebSocket.connections.push(this);
  }

  close() {}

  open() {
    this.onopen?.();
  }

  emit(message: object) {
    this.onmessage?.(
      new MessageEvent("message", { data: JSON.stringify(message) }),
    );
  }
}

class FakeAudioContext {
  static contexts: FakeAudioContext[] = [];
  static rejectResume = false;

  state: AudioContextState = "suspended";
  currentTime = 0;
  destination = {} as AudioDestinationNode;
  decodeAudioData = vi.fn(async (data: ArrayBuffer) => {
    const asset = new TextDecoder().decode(data);
    return { asset } as unknown as AudioBuffer;
  });
  playedAssets: string[] = [];

  constructor() {
    FakeAudioContext.contexts.push(this);
  }

  createGain() {
    return {
      connect: vi.fn().mockReturnThis(),
      gain: { setValueAtTime: vi.fn() },
    } as unknown as GainNode;
  }

  createBufferSource() {
    const source = {
      buffer: null as AudioBuffer | null,
      connect: vi.fn().mockReturnThis(),
      start: () => {
        this.playedAssets.push(
          (source.buffer as unknown as { asset: string }).asset,
        );
      },
    };
    return source as unknown as AudioBufferSourceNode;
  }

  async resume() {
    if (FakeAudioContext.rejectResume) throw new Error("playback rejected");
    this.state = "running";
  }
}

beforeEach(() => {
  attention = [];
  FakeWebSocket.connections = [];
  FakeAudioContext.contexts = [];
  FakeAudioContext.rejectResume = false;
  vi.stubGlobal("WebSocket", FakeWebSocket);
  vi.stubGlobal("AudioContext", FakeAudioContext);
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.startsWith("/audio/"))
        return Promise.resolve({
          ok: true,
          arrayBuffer: async () => new TextEncoder().encode(url).buffer,
        });
      if (url.includes("/acknowledge")) {
        attention = attention.map((item) => ({ ...item, acknowledged: true }));
        return Promise.resolve({ ok: true, json: async () => attention });
      }
      return Promise.resolve({ ok: true, json: async () => ({ attention }) });
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("useApprovalAttention", () => {
  it("WebSocket接続時にRESTで通知状態を再同期する", async () => {
    const { result } = renderHook(() => useApprovalAttention());

    await waitFor(() => expect(result.current.attention).toEqual([]));
    attention = [
      {
        target: "worktree",
        event: "response_completed",
        project: "whub-dev",
        issue_number: 116,
        operator_id: null,
        tool_name: null,
        requested_at: "2026-08-05T00:00:00+00:00",
        acknowledged: false,
      },
    ];

    act(() => FakeWebSocket.connections[0]?.open());

    await waitFor(() => expect(result.current.attention).toEqual(attention));
  });

  it("既読化直後にブラウザタブの通知を消す", async () => {
    attention = [
      {
        target: "worktree",
        event: "response_completed",
        project: "whub-dev",
        issue_number: 116,
        operator_id: null,
        tool_name: null,
        requested_at: "2026-08-05T00:00:00+00:00",
        acknowledged: false,
      },
    ];
    const { result } = renderHook(() => useApprovalAttention());

    await waitFor(() => expect(document.title).toBe("🔔 (1) whub"));
    await act(() => result.current.acknowledgeWorktree("whub-dev", 116));

    await waitFor(() => expect(document.title).toBe("whub"));
    expect(
      document.head.querySelector('[data-whub-attention-icon="true"]'),
    ).toBeNull();
  });

  it("通常の最初の操作で音声を起動し、WebSocketイベントで直ちに通知音を鳴らす", async () => {
    const { result } = renderHook(() => useApprovalAttention());

    act(() => window.dispatchEvent(new Event("pointerdown")));
    await waitFor(() =>
      expect(FakeAudioContext.contexts[0]?.state).toBe("running"),
    );
    await waitFor(() =>
      expect(
        FakeAudioContext.contexts[0]?.decodeAudioData,
      ).toHaveBeenCalledTimes(2),
    );

    attention = [
      {
        target: "worktree",
        event: "response_completed",
        project: "whub-dev",
        issue_number: 116,
        operator_id: null,
        tool_name: null,
        requested_at: "2026-08-05T00:00:00+00:00",
        acknowledged: false,
      },
    ];
    act(() =>
      FakeWebSocket.connections[0]?.emit({
        type: "attention_updated",
        event: "response_completed",
      }),
    );

    await waitFor(() => expect(result.current.attention).toEqual(attention));
    await waitFor(() =>
      expect(FakeAudioContext.contexts[0]?.playedAssets).toEqual([
        "/audio/response-completed.ogg",
      ]),
    );

    act(() =>
      FakeWebSocket.connections[0]?.emit({
        type: "attention_updated",
        event: "permission_request",
      }),
    );
    await waitFor(() =>
      expect(FakeAudioContext.contexts[0]?.playedAssets).toEqual([
        "/audio/response-completed.ogg",
        "/audio/permission-request.ogg",
      ]),
    );
  });

  it("通知状態の再取得に失敗してもWebSocketイベントの音を鳴らす", async () => {
    renderHook(() => useApprovalAttention());

    act(() => window.dispatchEvent(new Event("pointerdown")));
    await waitFor(() =>
      expect(
        FakeAudioContext.contexts[0]?.decodeAudioData,
      ).toHaveBeenCalledTimes(2),
    );
    vi.mocked(fetch).mockRejectedValue(new Error("request failed"));

    act(() =>
      FakeWebSocket.connections[0]?.emit({
        type: "attention_updated",
        event: "response_completed",
      }),
    );

    await waitFor(() =>
      expect(FakeAudioContext.contexts[0]?.playedAssets).toEqual([
        "/audio/response-completed.ogg",
      ]),
    );
  });

  it("初回起動後に停止した音声を次の通常操作で再開する", async () => {
    renderHook(() => useApprovalAttention());

    act(() => window.dispatchEvent(new Event("pointerdown")));
    await waitFor(() =>
      expect(FakeAudioContext.contexts[0]?.state).toBe("running"),
    );
    const context = FakeAudioContext.contexts[0];
    if (!context) throw new Error("audio context unavailable");
    context.state = "suspended";

    act(() => window.dispatchEvent(new Event("keydown")));

    await waitFor(() => expect(context.state).toBe("running"));
  });

  it("通知音が拒否されても次の通常操作で再試行する", async () => {
    FakeAudioContext.rejectResume = true;
    renderHook(() => useApprovalAttention());

    act(() => window.dispatchEvent(new Event("pointerdown")));
    await waitFor(() => expect(FakeAudioContext.contexts).toHaveLength(1));
    FakeAudioContext.rejectResume = false;
    act(() => window.dispatchEvent(new Event("keydown")));

    await waitFor(() =>
      expect(FakeAudioContext.contexts[0]?.state).toBe("running"),
    );
  });
});
