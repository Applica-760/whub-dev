import { useCallback, useEffect, useRef, useState } from "react";

import {
  acknowledgeApprovalAttention,
  listApprovalAttention,
} from "./attentionApi";
import type { ApprovalAttention } from "./attentionApi";

const POLL_INTERVAL_MS = 5_000;

function attentionKey(item: ApprovalAttention) {
  return `${item.project}/${item.task_id}/${item.tool_name}/${item.requested_at}`;
}

function notify(item: ApprovalAttention) {
  if (
    document.hidden &&
    typeof Notification !== "undefined" &&
    Notification.permission === "granted"
  ) {
    new Notification("whub: 承認待ち", {
      body: `${item.project} / ${item.task_id} が承認を待っています。`,
    });
  }
}

export function useApprovalAttention() {
  const [attention, setAttention] = useState<ApprovalAttention[]>([]);
  const known = useRef(new Set<string>());

  const refresh = useCallback(async () => {
    try {
      const response = await listApprovalAttention();
      for (const item of response.attention) {
        const key = attentionKey(item);
        if (!item.acknowledged && !known.current.has(key)) notify(item);
        known.current.add(key);
      }
      known.current = new Set(response.attention.map(attentionKey));
      setAttention(response.attention);
    } catch {
      // Approval attention is supplementary; retain the latest visible state.
    }
  }, []);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => void refresh(), POLL_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [refresh]);

  const acknowledge = useCallback(async (project: string, taskId: string) => {
    try {
      const updated = await acknowledgeApprovalAttention(project, taskId);
      if (updated === null) return;
      setAttention((current) =>
        current.map((item) =>
          item.project === project && item.task_id === taskId ? updated : item,
        ),
      );
    } catch {
      // The next poll retries synchronization with the control plane.
    }
  }, []);

  return { acknowledge, attention };
}
