import { requestJson } from "../../api/client";
import { errorMessage } from "../../api/errorMessage";
import type { paths } from "../../api/generated/schema";
import { useCallback, useEffect, useState } from "react";

type AgentSessionList =
  paths["/api/agent-sessions"]["get"]["responses"][200]["content"]["application/json"];
export type AgentSession = AgentSessionList["sessions"][number];

export function useAgentSessions() {
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSessions((await requestJson<AgentSessionList>("/api/agent-sessions")).sessions);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => void refresh(), [refresh]);
  return { error, loading, sessions };
}
