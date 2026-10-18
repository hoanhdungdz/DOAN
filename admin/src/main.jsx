import React from "react";
import DialogProvider from "../../shared/DialogProvider";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
} from "react-router-dom";
import { SessionProvider } from "../../shared/session";
import AuthPage from "../../shared/AuthPage";
import AdminLayout from "./layouts/AdminLayout";
import DashboardPage from "./pages/DashboardPage";
import ResourcePage from "./pages/ResourcePage";
import OrdersPage from "./pages/OrdersPage";
import POSPage from "./pages/POSPage";
import InvoicePage from "./pages/InvoicePage";
import "../../shared/styles.css";
import "./styles.css";
function ResourceRoute() {
  const loc = useLocation();
  return <ResourcePage key={loc.pathname} />;
}
function App() {
  return (
    <Routes>
      {["login", "forgot-password", "reset-password"].map((mode) => (
        <Route
          key={mode}
          path={"/" + mode}
          element={<AuthPage mode={mode} internal />}
        />
      ))}
      <Route element={<AdminLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="reports" element={<DashboardPage report />} />
        <Route path="orders" element={<OrdersPage />} />
        <Route path="orders/:id" element={<OrdersPage />} />
        <Route path="pos" element={<POSPage />} />
        <Route path="invoices/:id" element={<InvoicePage />} />
        <Route path=":resource" element={<ResourceRoute />} />
      </Route>
    </Routes>
  );
}
createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <SessionProvider>
      <DialogProvider>
        <App />
      </DialogProvider>
    </SessionProvider>
  </BrowserRouter>,
);
