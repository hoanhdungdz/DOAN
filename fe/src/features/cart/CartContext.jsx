import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "../../../../shared/api";
import { useSession } from "../../../../shared/session";
const Context = createContext(null),
  storage = "tech-retail-cart";
function readGuest() {
  try {
    const v = JSON.parse(localStorage.getItem(storage) || "[]");
    return Array.isArray(v)
      ? v
          .filter(
            (x) =>
              Number.isSafeInteger(x.variant) &&
              Number.isSafeInteger(x.quantity) &&
              x.quantity > 0 &&
              x.quantity <= 1000,
          )
          .slice(0, 100)
      : [];
  } catch {
    return [];
  }
}
export function CartProvider({ children }) {
  const { user, loading: sessionLoading } = useSession(),
    [items, setItems] = useState([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  async function refresh() {
    setLoading(true);
    setError("");
    try {
      if (user) {
        const d = await api("carts/");
        setItems(
          d.items.map(({ variant, quantity, details }) => ({
            variant,
            quantity,
            details,
          })),
        );
        setError((d.warnings || []).join(" "));
      } else setItems(readGuest());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    if (!sessionLoading) refresh();
  }, [user?.id, sessionLoading]);
  async function merge() {
    const guest = readGuest();
    let warnings = [];
    if (guest.length) {
      const merged = await api("carts/", {
        method: "POST",
        body: { items: guest },
      });
      warnings = merged.warnings || [];
      localStorage.removeItem(storage);
    }
    const d = await api("carts/");
    setItems(d.items);
    warnings = [...warnings, ...(d.warnings || [])];
    setError(warnings.join(" "));
    return warnings;
  }
  async function replace(next) {
    const clean = next
      .filter((x) => x.quantity > 0)
      .map(({ variant, quantity }) => ({ variant, quantity }));
    if (
      clean.some(
        (x) =>
          !Number.isSafeInteger(x.quantity) ||
          x.quantity > 1000 ||
          !Number.isSafeInteger(x.variant),
      )
    )
      throw new Error("Số lượng phải là số nguyên dương, tối đa 1000.");
    if (user) {
      const d = await api("carts/", { method: "PUT", body: { items: clean } });
      setItems(d.items);
      setError((d.warnings || []).join(" "));
    } else {
      localStorage.setItem(storage, JSON.stringify(clean));
      setItems(clean);
    }
  }
  async function add(variant, quantity = 1) {
    if (!Number.isSafeInteger(quantity) || quantity < 1)
      throw new Error("Số lượng phải là số nguyên dương.");
    const found = items.find((x) => x.variant === variant);
    if ((found?.quantity || 0) + quantity > 1000)
      throw new Error("Tối đa 1000 đơn vị mỗi sản phẩm.");
    await replace(
      found
        ? items.map((x) =>
            x.variant === variant
              ? { ...x, quantity: x.quantity + quantity }
              : x,
          )
        : [...items, { variant, quantity }],
    );
  }
  return (
    <Context.Provider
      value={{
        items,
        loading,
        error,
        add,
        replace,
        merge,
        refresh,
        clear: () => replace([]),
        count: items.reduce((n, x) => n + x.quantity, 0),
      }}
    >
      {children}
    </Context.Provider>
  );
}
export const useCart = () => useContext(Context);
