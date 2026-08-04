import { useCallback, useEffect, useState } from "react";

import {
  acknowledgeOperatorAttention,
  acknowledgeWorktreeAttention,
  listApprovalAttention,
} from "./attentionApi";
import type { ApprovalAttention } from "./attentionApi";

const POLL_INTERVAL_MS = 5_000;
const DEFAULT_TITLE = "whub";
const ATTENTION_ICON = "/attention-favicon.svg";

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

  const refresh = useCallback(async () => {
    try {
      const response = await listApprovalAttention();
      setAttention(response.attention);
      setTabAttention(response.attention);
    } catch {
      // Approval attention is supplementary; retain the latest visible state.
    }
  }, []);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => void refresh(), POLL_INTERVAL_MS);
    return () => {
      window.clearInterval(interval);
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

  return { acknowledgeOperator, acknowledgeWorktree, attention };
}
