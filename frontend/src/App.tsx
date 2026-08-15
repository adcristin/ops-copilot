import { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import SignupPage from "./pages/SignupPage";
import LoginPage from "./pages/LoginPage";
import AuthCallbackPage from "./pages/AuthCallbackPage";
import DashboardPage from "./pages/DashboardPage";
import AccountPage from "./pages/AccountPage";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { PublicRoute } from "./components/PublicRoute";
import { LoadingScreen } from "./components/LoadingScreen";
import { api, isAuthenticated } from "./api";
import type { User } from "./types";

export default function App() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (isAuthenticated() && !user) {
      api.me().then(setUser).catch(() => setUser(null));
    }
  }, [user]);

  const handleLogout = () => {
    api.logout();
    setUser(null);
  };

  return (
    <Routes>
      <Route element={<PublicRoute />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth-callback" element={<AuthCallbackPage />} />
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route
          path="/dashboard"
          element={user ? <DashboardPage user={user} onLogout={handleLogout} /> : <LoadingScreen message="Waking up the server, this can take up to a minute..." />}
        />
        <Route
          path="/account"
          element={user ? <AccountPage user={user} /> : <LoadingScreen message="Loading account settings..." />}
        />
      </Route>
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}
