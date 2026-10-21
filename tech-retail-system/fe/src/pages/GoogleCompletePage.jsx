import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useSession } from "../../../shared/session";
import { customerReturnPath } from "../../../shared/returnPath";
import { errorText } from "../../../shared/api";
import { Loading, ErrorBox } from "../../../shared/ui";
import { useCart } from "../features/cart/CartContext";

export default function GoogleCompletePage({ provider = "google" }) {
  const providerName = provider === "facebook" ? "Facebook" : "Google";
  const { user, loading, error: sessionError } = useSession();
  const { merge } = useCart();
  const navigate = useNavigate(),
    [params] = useSearchParams();
  const [error, setError] = useState("");
  const currentMerge = useRef(merge);
  currentMerge.current = merge;
  const next = customerReturnPath(params.get("next"));
  const linked = params.get("linked") === "1";
  useEffect(() => {
    if (loading || !user) return;
    let live = true;
    (async () => {
      try {
        const warnings = linked ? [] : await currentMerge.current();
        if (live)
          navigate(
            linked
              ? `/profile?${provider}_linked=1`
              : next || (warnings?.length ? "/cart" : "/"),
            {
              replace: true,
              state: warnings?.length
                ? { notice: warnings.join(" ") }
                : undefined,
            },
          );
      } catch (e) {
        if (live) setError(errorText(e));
      }
    })();
    return () => {
      live = false;
    };
  }, [loading, user?.id, next, linked, navigate, provider]);
  const failure =
    error ||
    sessionError ||
    (!loading && !user
      ? "Phiên đăng nhập không còn hiệu lực. Vui lòng đăng nhập lại."
      : "");
  return (
    <main className="content-width account-page">
      <h1>
        {linked ? `Liên kết ${providerName}` : `Đăng nhập ${providerName}`}
      </h1>
      {failure ? (
        <>
          <ErrorBox error={failure} />
          <Link to={user ? "/cart" : "/login"}>
            {user ? "Mở giỏ hàng để kiểm tra" : "Quay lại đăng nhập"}
          </Link>
        </>
      ) : (
        <Loading />
      )}
    </main>
  );
}
