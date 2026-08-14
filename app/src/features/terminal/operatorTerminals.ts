import { useCallback, useEffect, useState } from "react";

import { requestJson } from "../../api/client";
import { errorMessage } from "../../api/errorMessage";
import type { paths } from "../../api/generated/schema";

type OperatorTerminals =
  paths["/api/operator-terminals"]["get"]["responses"][200]["content"]["application/json"];
export type OperatorTerminal = OperatorTerminals["terminals"][number];

export function useOperatorTerminals() {
  const [operators, setOperators] = useState<OperatorTerminal[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [pending, setPending] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const listed = await requestJson<OperatorTerminals>(
        "/api/operator-terminals",
      );
      setOperators((current) =>
        current.length === listed.terminals.length &&
        current.every(
          (operator, index) =>
            operator.operator_id === listed.terminals[index]?.operator_id,
        )
          ? current
          : listed.terminals,
      );
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => void refresh(), [refresh]);

  const startOperator = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      const created = await requestJson<OperatorTerminal>(
        "/api/operator-terminals",
        { method: "POST" },
      );
      setOperators((current) => [...current, created]);
      return created;
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setPending(false);
    }
  }, []);

  const stopOperator = useCallback(async (operatorId: string) => {
    setPending(true);
    setError(null);
    try {
      await requestJson<void>(
        `/api/operator-terminals/${encodeURIComponent(operatorId)}`,
        { method: "DELETE" },
      );
      setOperators((current) =>
        current.filter((operator) => operator.operator_id !== operatorId),
      );
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setPending(false);
    }
  }, []);

  return { error, loaded, operators, pending, startOperator, stopOperator };
}
