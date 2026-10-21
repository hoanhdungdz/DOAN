import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useSession } from "../../../shared/session";
import { Loading, ErrorBox } from "../../../shared/ui";

export default function RequireAccount({ children }) {
  const { user, loading, error, refresh } = useSession();
  const location = useLocation();
  if (loading) return <Loading />;
  if (error)
    return (
      <main className="content-width panel">
        <ErrorBox error={error} />
        <button onClick={refresh}>Thử lại</button>
      </main>
    );
  if (!user)
    return (
      <Navigate
        to={
          "/login?next=" +
          encodeURIComponent(location.pathname + location.search)
        }
        replace
      />
    );
  // Discard another account's screen state immediately when the session changes.
  return <React.Fragment key={user.id}>{children}</React.Fragment>;
}
