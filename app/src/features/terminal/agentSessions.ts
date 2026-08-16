import { requestJson } from "../../api/client";
import { errorMessage } from "../../api/errorMessage";
import { listProjects } from "../projects/api";
import type { paths } from "../../api/generated/schema";
import { useCallback, useEffect, useState } from "react";

type AgentSessionList =
  paths["/api/agent-sessions/{project}"]["get"]["responses"][200]["content"]["application/json"];
export type AgentSession = AgentSessionList["sessions"][number];
const LOADING_INDICATOR_TIMEOUT_MS = 5_000;
const SESSION_REQUEST_TIMEOUT_MS = 10_000;

export function useAgentSessions() {
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const projects = await listProjects();
      let pending = projects.length;
      if (!pending) setLoading(false);
      for (const project of projects)
        void requestJson<AgentSessionList>(
          `/api/agent-sessions/${encodeURIComponent(project)}`,
          { signal: AbortSignal.timeout(SESSION_REQUEST_TIMEOUT_MS) },
        )
          .then((listed) =>
            setSessions((current) => [...current, ...listed.sessions]),
          )
          .catch(() => undefined)
          .finally(() => {
            pending -= 1;
            if (!pending) setLoading(false);
          });
    } catch (requestError) {
      setError(errorMessage(requestError));
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    void refresh();
    const timeout = window.setTimeout(
      () => setLoading(false),
      LOADING_INDICATOR_TIMEOUT_MS,
    );
    return () => window.clearTimeout(timeout);
  }, [refresh]);
  return { error, loading, sessions };
}
