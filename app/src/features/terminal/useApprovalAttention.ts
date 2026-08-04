import { useCallback, useEffect, useRef, useState } from "react";

import {
  acknowledgeOperatorAttention,
  acknowledgeWorktreeAttention,
  listApprovalAttention,
} from "./attentionApi";
import type { ApprovalAttention } from "./attentionApi";

const DEFAULT_TITLE = "whub";
const ATTENTION_ICON = "/attention-favicon.svg";
const RECONNECT_DELAY_MS = 1_000;
type NotificationEvent = "permission_request" | "response_completed";

function setTabAttention(attention: ApprovalAttention[]) {
  const count = attention.filter((item) => !item.acknowledged).length;
  document.title = count ? `🔔 (${count}) ${DEFAULT_TITLE}` : DEFAULT_TITLE;
  const selector = 'link[data-whub-attention-icon="true"]';
  const existing = document.head.querySelector<HTMLLinkElement>(selector);
  if (!count) {
    existing?.remove();
    return;
  }
  const icon = existing ?? document.createElement("link");
  icon.rel = "icon";
  icon.type = "image/svg+xml";
  icon.dataset.whubAttentionIcon = "true";
  icon.href = ATTENTION_ICON;
  if (!existing) document.head.append(icon);
}

export function useApprovalAttention() {
  const [attention, setAttention] = useState<ApprovalAttention[]>([]);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const audioContext = useRef<AudioContext | null>(null);

  const playSound = useCallback(() => {
    try {
      const context = audioContext.current;
      if (!context || context.state !== "running")
        throw new Error("audio unavailable");
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.frequency.value = 880;
      gain.gain.setValueAtTime(0.08, context.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.16);
      oscillator.connect(gain).connect(context.destination);
      oscillator.start();
      oscillator.stop(context.currentTime + 0.16);
    } catch {
      setSoundEnabled(false);
    }
  }, []);

  const enableSound = useCallback(async () => {
    try {
      const AudioContextConstructor = window.AudioContext;
      if (!AudioContextConstructor) throw new Error("audio unavailable");
      const context = audioContext.current ?? new AudioContextConstructor();
      audioContext.current = context;
      await context.resume();
      setSoundEnabled(true);
    } catch {
      setSoundEnabled(false);
    }
  }, []);

  const refresh = useCallback(
    async (event?: NotificationEvent) => {
      try {
        const response = await listApprovalAttention();
        setAttention(response.attention);
        setTabAttention(response.attention);
        if (event) playSound();
      } catch {
        // Approval attention is supplementary; retain the latest visible state.
      }
    },
    [playSound],
  );

  useEffect(() => {
    void refresh();
    if (!("WebSocket" in window)) return;
    let reconnectTimer: number | undefined;
    let closed = false;
    let socket: WebSocket | undefined;
    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(
        `${protocol}//${window.location.host}/api/agent-attention/stream`,
      );
      socket.onmessage = (message) => {
        try {
          const payload = JSON.parse(message.data) as {
            event?: NotificationEvent;
            type?: string;
          };
          if (payload.type === "attention_updated") void refresh(payload.event);
        } catch {
          // A malformed supplementary event is ignored until reconnect synchronization.
        }
      };
      socket.onclose = () => {
        if (!closed)
          reconnectTimer = window.setTimeout(connect, RECONNECT_DELAY_MS);
      };
    };
    connect();
    return () => {
      closed = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      socket?.close();
      setTabAttention([]);
    };
  }, [refresh]);

  const acknowledgeWorktree = useCallback(
    async (project: string, taskId: string) => {
      try {
        const updated = await acknowledgeWorktreeAttention(project, taskId);
        setAttention((current) =>
          current.map(
            (item) =>
              updated.find(
                (updatedItem) =>
                  updatedItem.target === item.target &&
                  updatedItem.event === item.event &&
                  updatedItem.project === item.project &&
                  updatedItem.task_id === item.task_id,
              ) ?? item,
          ),
        );
      } catch {
        // The next poll retries synchronization with the control plane.
      }
    },
    [],
  );

  const acknowledgeOperator = useCallback(async (operatorId: string) => {
    try {
      const updated = await acknowledgeOperatorAttention(operatorId);
      setAttention((current) =>
        current.map(
          (item) =>
            updated.find(
              (updatedItem) =>
                updatedItem.target === item.target &&
                updatedItem.event === item.event &&
                updatedItem.operator_id === item.operator_id,
            ) ?? item,
        ),
      );
    } catch {
      // The next poll retries synchronization with the control plane.
    }
  }, []);

  return {
    acknowledgeOperator,
    acknowledgeWorktree,
    attention,
    enableSound,
    soundEnabled,
  };
}
