import React from "react";
import DialogProvider from "../../shared/DialogProvider";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { SessionProvider } from "../../shared/session";
import { CartProvider, useCart } from "./features/cart/CartContext";
import AuthPage from "../../shared/AuthPage";
import CustomerLayout from "./layouts/CustomerLayout";
import CatalogPage from "./pages/CatalogPage";
import ProductDetail from "./pages/ProductDetail";
import CartCheckout from "./pages/CartCheckout";
import { OrderPage, ProfilePage } from "./pages/AccountPages";
import RequireAccount from "./components/RequireAccount";
import GoogleCompletePage from "./pages/GoogleCompletePage";
import VnpayReturnPage from "./pages/VnpayReturnPage";
import "../../shared/styles.css";
import "./styles.css";
function Auth({ mode }) {
  const { merge } = useCart();
  return <AuthPage mode={mode} onAuthenticated={merge} />;
}
function App() {
  return (
    <Routes>
      {["login", "register", "forgot-password", "reset-password"].map(
        (mode) => (
          <Route key={mode} path={"/" + mode} element={<Auth mode={mode} />} />
        ),
      )}
      <Route element={<CustomerLayout />}>
        <Route path="payments/vnpay/return" element={<VnpayReturnPage />} />
        <Route path="auth/google/complete" element={<GoogleCompletePage />} />
        <Route
          path="auth/facebook/complete"
          element={<GoogleCompletePage provider="facebook" />}
        />
        <Route index element={<CatalogPage home />} />
        <Route path="products" element={<CatalogPage />} />
        <Route path="products/:slug" element={<ProductDetail />} />
        <Route path="cart" element={<CartCheckout />} />
        <Route
          path="checkout"
          element={
            <RequireAccount>
              <CartCheckout checkout />
            </RequireAccount>
          }
        />
        <Route
          path="orders"
          element={
            <RequireAccount>
              <OrderPage />
            </RequireAccount>
          }
        />
        <Route
          path="orders/:id"
          element={
            <RequireAccount>
              <OrderPage />
            </RequireAccount>
          }
        />
        <Route path="lookup" element={<Navigate to="/orders" replace />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route
          path="*"
          element={
            <div className="success panel">
              <h1>Trang không tồn tại.</h1>
              <a href="/">Về trang chủ</a>
            </div>
          }
        />
      </Route>
    </Routes>
  );
}
createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <SessionProvider>
      <CartProvider>
        <DialogProvider>
          <App />
        </DialogProvider>
      </CartProvider>
    </SessionProvider>
  </BrowserRouter>,
);
