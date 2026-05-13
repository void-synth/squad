import { Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout.jsx";
import AlertsInboxPage from "./pages/AlertsInboxPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import TransactionDetailPage from "./pages/TransactionDetailPage.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/transactions/:ref" element={<TransactionDetailPage />} />
        <Route path="/alerts" element={<AlertsInboxPage />} />
      </Route>
    </Routes>
  );
}
