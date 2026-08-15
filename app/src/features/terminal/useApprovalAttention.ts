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
const SOUND_ASSETS: Record<NotificationEvent, string> = {
  permission_request: "/audio/permission-request.ogg",
  response_completed: "/audio/response-completed.ogg",
};

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
  const audioContext = useRef<AudioContext | null>(null);
  const refreshVersion = useRef(0);
  const soundBuffers = useRef<Partial<Record<NotificationEvent, AudioBuffer>>>(
    {},
  );

  const loadSoundBuffers = useCallback(async (context: AudioContext) => {
    const loaded = await Promise.all(
      (Object.entries(SOUND_ASSETS) as [NotificationEvent, string][]).map(
        async ([event, path]) => {
          const response = await fetch(path);
          if (!response.ok) throw new Error("sound unavailable");
          const buffer = await context.decodeAudioData(
            await response.arrayBuffer(),
          );
          return [event, buffer] as const;
        },
      ),
    );
    soundBuffers.current = Object.fromEntries(loaded);
  }, []);

  const activateSound = useCallback(async () => {
    try {
      const AudioContextConstructor = window.AudioContext;
      if (!AudioContextConstructor) return false;
      const context = audioContext.current ?? new AudioContextConstructor();
      audioContext.current = context;
      await context.resume();
      if (
        context.state === "running" &&
        !soundBuffers.current.permission_request
      )
        await loadSoundBuffers(context);
      return context.state === "running";
    } catch {
      return false;
    }
  }, [loadSoundBuffers]);

  const playSound = useCallback(
    async (event: NotificationEvent) => {
      try {
        if (!(await activateSound())) throw new Error("audio unavailable");
        const context = audioContext.current;
        const buffer = soundBuffers.current[event];
        if (!context || !buffer) throw new Error("sound unavailable");
        const source = context.createBufferSource();
        const gain = context.createGain();
        source.buffer = buffer;
        gain.gain.setValueAtTime(0.35, context.currentTime);
        source.connect(gain).connect(context.destination);
        source.start();
      } catch {
        // Browsers block audio until a user interaction; the badge remains visible.
      }
    },
    [activateSound],
  );

  const refresh = useCallback(async () => {
    const version = ++refreshVersion.current;
    try {
      const response = await listApprovalAttention();
      if (version !== refreshVersion.current) return;
      setAttention(response.attention);
    } catch {
      // Approval attention is supplementary; retain the latest visible state.
    }
  }, []);

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
      socket.onopen = () => {
        void refresh();
      };
      socket.onmessage = (message) => {
        try {
          const payload = JSON.parse(message.data) as {
            event?: NotificationEvent;
            type?: string;
          };
          if (payload.type === "attention_updated") {
            if (payload.event) void playSound(payload.event);
            void refresh();
          }
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
  }, [playSound, refresh]);

  useEffect(() => {
    setTabAttention(attention);
  }, [attention]);

  useEffect(() => {
    const activate = () => {
      void activateSound();
    };
    window.addEventListener("pointerdown", activate, true);
    window.addEventListener("keydown", activate, true);
    return () => {
      window.removeEventListener("pointerdown", activate, true);
      window.removeEventListener("keydown", activate, true);
    };
  }, [activateSound]);

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
        void refresh();
      } catch {
        // The next poll retries synchronization with the control plane.
      }
    },
    [refresh],
  );

  const acknowledgeOperator = useCallback(
    async (operatorId: string) => {
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
        void refresh();
      } catch {
        // The next poll retries synchronization with the control plane.
      }
    },
    [refresh],
  );

  return {
    acknowledgeOperator,
    acknowledgeWorktree,
    attention,
  };
}
