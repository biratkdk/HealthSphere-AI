import { useEffect, useState } from "react";

import { getOperationsStreamToken, getOperationsStreamUrl, getRequestErrorMessage } from "../services/api";

export const useOperationsStream = (enabled = true) => {
  const [snapshot, setSnapshot] = useState(null);
  const [connected, setConnected] = useState(false);
  const [lastEventAt, setLastEventAt] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!enabled || typeof window === "undefined" || typeof window.EventSource === "undefined") {
      return undefined;
    }

    let closed = false;
    let reconnectTimer = null;
    let eventSource = null;

    const closeCurrentStream = () => {
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
    };

    const connect = async () => {
      try {
        const token = await getOperationsStreamToken();
        if (closed) {
          return;
        }

        closeCurrentStream();
        eventSource = new window.EventSource(getOperationsStreamUrl(token.stream_token));
        eventSource.addEventListener("open", () => {
          setConnected(true);
          setError("");
        });
        eventSource.addEventListener("operations", (event) => {
          const payload = JSON.parse(event.data);
          setSnapshot(payload);
          setLastEventAt(payload.generated_at || new Date().toISOString());
        });
        eventSource.addEventListener("heartbeat", (event) => {
          const payload = JSON.parse(event.data);
          setLastEventAt(payload.generated_at || new Date().toISOString());
        });
        eventSource.onerror = () => {
          setConnected(false);
          closeCurrentStream();
          if (!closed) {
            reconnectTimer = window.setTimeout(connect, 3000);
          }
        };
      } catch (streamError) {
        if (!closed) {
          setConnected(false);
          setError(getRequestErrorMessage(streamError, "Live stream unavailable."));
          reconnectTimer = window.setTimeout(connect, 5000);
        }
      }
    };

    connect();

    return () => {
      closed = true;
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
      }
      closeCurrentStream();
    };
  }, [enabled]);

  return {
    snapshot,
    connected,
    lastEventAt,
    error,
  };
};
