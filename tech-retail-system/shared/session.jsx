import React, { useCallback, useEffect, useRef, useState } from "react";
import { SessionContext as Context } from "./sessionContext";
import { api } from "./api";
export function SessionProvider({ children }) {
  const [user, setUser] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const generation = useRef(0),
    flight = useRef(null);
  const refresh = useCallback(() => {
    if (flight.current) return flight.current;
    const version = generation.current;
    // Revalidate in the background: an unchanged session must not discard a
    // checkout form merely because the user switched browser tabs.
    const pending = api("auth/me/")
      .then((d) => {
        if (version === generation.current) {
          setUser(d.user);
          setError("");
        }
      })
      .catch((e) => {
        if (version === generation.current) {
          setUser(null);
          setError(e.message);
        }
      })
      .finally(() => {
        if (version === generation.current) setLoading(false);
        if (flight.current === pending) flight.current = null;
      });
    flight.current = pending;
    return pending;
  }, []);
  useEffect(() => {
    refresh();
    const visible = () => {
      if (document.visibilityState !== "hidden") refresh();
    };
    window.addEventListener("focus", visible);
    document.addEventListener("visibilitychange", visible);
    return () => {
      generation.current++;
      flight.current = null;
      window.removeEventListener("focus", visible);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [refresh]);
  const authenticate = async (action, body) => {
    const d = await api(`auth/${action}/`, { method: "POST", body });
    generation.current++;
    flight.current = null;
    setUser(d.user);
    setError("");
    setLoading(false);
    return d.user;
  };
  const signOut = async () => {
    await api("auth/logout/", { method: "POST", body: {} });
    generation.current++;
    flight.current = null;
    setUser(null);
    setError("");
    setLoading(false);
  };
  return (
    <Context.Provider
      value={{ user, loading, error, authenticate, signOut, refresh }}
    >
      {children}
    </Context.Provider>
  );
}
export { useSession } from "./sessionContext";
