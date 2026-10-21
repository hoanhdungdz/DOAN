import { useEffect, useRef, useState } from "react";
import { api, errorText } from "./api";

const WINDOW_MS = 60000;
const QUERY_AT = [0, 15000, 35000, 55000];

export function vnpayOutcome(attempt) {
  if (
    attempt.status === "REVIEW" ||
    attempt.order_payment_status === "REFUND_PENDING"
  )
    return "review";
  if (attempt.order_payment_status === "REFUNDED") return "refunded";
  if (attempt.status === "SUCCEEDED" && attempt.order_payment_status === "PAID")
    return "success";
  if (attempt.status === "FAILED") return "failed";
  return "verifying";
}

// Return-page recovery only: GET remains read-only; QueryDR uses the existing owner/CSRF POST.
export default function useVnpayResult(reference, refreshSession) {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState({
    phase: "verifying",
    attempt: null,
    order: null,
    error: "",
  });
  const sessionRefresh = useRef(refreshSession);
  sessionRefresh.current = refreshSession;
  useEffect(() => {
    let live = true,
      running = false,
      stopped = false,
      timer,
      order = null,
      queryCount = 0;
    const started = Date.now(),
      deadline = started + WINDOW_MS;
    setState({ phase: "verifying", attempt: null, order: null, error: "" });
    const publish = (attempt) => {
      const phase = vnpayOutcome(attempt);
      stopped = phase !== "verifying";
      setState({ phase, attempt, order, error: "" });
    };
    const onError = (error) => {
      if ([401, 403, 404].includes(error.status)) {
        stopped = true;
        setState({
          phase: "denied",
          attempt: null,
          order: null,
          error:
            "Không tìm thấy thanh toán của tài khoản này. Hãy đăng nhập tài khoản đã đặt đơn.",
        });
        sessionRefresh.current?.();
      } else {
        // A provider/network error is not evidence that a payment failed.
        if (error.status === 429) queryCount = QUERY_AT.length;
        setState((previous) => ({ ...previous, error: errorText(error) }));
      }
    };
    const tick = async () => {
      if (!live || stopped || running) return;
      running = true;
      try {
        let attempt = await api(`payments/vnpay/attempts/${reference}/`);
        if (!live) return;
        if (!order) {
          order = await api(`my-orders/${attempt.order}/`);
          if (!live) return;
        }
        publish(attempt);
        if (
          !stopped &&
          queryCount < QUERY_AT.length &&
          Date.now() >= started + QUERY_AT[queryCount] &&
          document.visibilityState !== "hidden"
        ) {
          queryCount++;
          attempt = await api(`payments/vnpay/attempts/${reference}/check/`, {
            method: "POST",
            body: {},
          });
          if (!live) return;
          publish(attempt);
        }
      } catch (error) {
        if (live) onError(error);
      } finally {
        running = false;
        if (live && !stopped) {
          if (Date.now() >= deadline) {
            stopped = true;
            setState((previous) => ({ ...previous, phase: "unconfirmed" }));
          } else
            timer = setTimeout(tick, Math.min(4000, deadline - Date.now()));
        }
      }
    };
    const resume = () => {
      if (document.visibilityState !== "hidden" && !running) {
        clearTimeout(timer);
        tick();
      }
    };
    tick();
    window.addEventListener("focus", resume);
    document.addEventListener("visibilitychange", resume);
    return () => {
      live = false;
      clearTimeout(timer);
      window.removeEventListener("focus", resume);
      document.removeEventListener("visibilitychange", resume);
    };
  }, [reference, revision]);
  return { ...state, retry: () => setRevision((value) => value + 1) };
}
