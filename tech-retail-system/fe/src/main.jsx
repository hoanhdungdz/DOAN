import React from "react";
import DialogProvider from "../../shared/DialogProvider";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { SessionProvider } from "../../shared/session";
import { CartProvider, useCart } from "./features/cart/CartContext";
import AuthPage from "../../shared/AuthPage";
import CustomerLayout from "./layouts/CustomerLayout";
import CatalogPage from "./pages/CatalogPage";
import ProductDetail from "./pages/ProductDetail";
import CartCheckout from "./pages/CartCheckout";
import { OrderPage, LookupPage, ProfilePage } from "./pages/AccountPages";
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
        <Route index element={<CatalogPage home />} />
        <Route path="products" element={<CatalogPage />} />
        <Route path="products/:slug" element={<ProductDetail />} />
        <Route path="cart" element={<CartCheckout />} />
        <Route path="checkout" element={<CartCheckout checkout />} />
        <Route path="orders" element={<OrderPage />} />
        <Route path="orders/:id" element={<OrderPage />} />
        <Route path="lookup" element={<LookupPage />} />
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
