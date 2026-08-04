import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useApprovalAttention } from "./useApprovalAttention";
import type { ApprovalAttention } from "./attentionApi";

let attention: ApprovalAttention[];

class FakeWebSocket {
  static connections: FakeWebSocket[] = [];

  onclose: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;

  constructor() {
    FakeWebSocket.connections.push(this);
  }

  close() {}

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
  oscillatorStart = vi.fn();

  constructor() {
    FakeAudioContext.contexts.push(this);
  }

  createGain() {
    return {
      connect: vi.fn().mockReturnThis(),
      gain: { exponentialRampToValueAtTime: vi.fn(), setValueAtTime: vi.fn() },
    } as unknown as GainNode;
  }

  createOscillator() {
    return {
      connect: vi.fn().mockReturnThis(),
      frequency: { value: 0 },
      start: this.oscillatorStart,
      stop: vi.fn(),
    } as unknown as OscillatorNode;
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
    vi.fn(() =>
      Promise.resolve({ ok: true, json: async () => ({ attention }) }),
    ),
  );
});

afterEach(() => vi.unstubAllGlobals());

describe("useApprovalAttention", () => {
  it("WebSocketイベントで直ちに同期し、有効化済みなら通知音を鳴らす", async () => {
    const { result } = renderHook(() => useApprovalAttention());

    await act(async () => result.current.enableSound());
    expect(result.current.soundEnabled).toBe(true);

    attention = [
      {
        target: "worktree",
        event: "response_completed",
        project: "whub-dev",
        task_id: "TASK-116",
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
    expect(
      FakeAudioContext.contexts[0]?.oscillatorStart,
    ).toHaveBeenCalledOnce();
  });

  it("通知音が拒否された場合は有効状態にしない", async () => {
    FakeAudioContext.rejectResume = true;
    const { result } = renderHook(() => useApprovalAttention());

    await act(async () => result.current.enableSound());

    expect(result.current.soundEnabled).toBe(false);
  });
});
