import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components";
import { LoginPage } from "./pages/LoginPage";
import { StationsPage } from "./pages/StationsPage";
import { DevicesPage } from "./pages/DevicesPage";
import { DeviceDetailPage } from "./pages/DeviceDetailPage";
import { AlarmsPage } from "./pages/AlarmsPage";

function ProtectedShell() {
  return localStorage.getItem("cer-session") ? <AppShell /> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedShell />}>
        <Route path="/stations" element={<StationsPage />} />
        <Route path="/devices" element={<DevicesPage />} />
        <Route path="/devices/:deviceId" element={<DeviceDetailPage />} />
        <Route path="/alarms" element={<AlarmsPage />} />
      </Route>
      <Route path="*" element={<Navigate to={localStorage.getItem("cer-session") ? "/stations" : "/login"} replace />} />
    </Routes>
  );
}

