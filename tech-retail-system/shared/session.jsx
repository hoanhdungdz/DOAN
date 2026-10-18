import React, { useEffect, useState } from "react";
import { SessionContext as Context } from "./sessionContext";
import { api } from "./api";
export function SessionProvider({ children }) {
  const [user, setUser] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const refresh = () =>
    api("auth/me/")
      .then((d) => {
        setUser(d.user);
        setError("");
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  useEffect(() => {
    refresh();
  }, []);
  const authenticate = async (action, body) => {
    const d = await api(`auth/${action}/`, { method: "POST", body });
    setUser(d.user);
    return d.user;
  };
  const signOut = async () => {
    await api("auth/logout/", { method: "POST", body: {} });
    setUser(null);
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
