import React, { useState, useEffect } from "react";
import { Lock } from "lucide-react";
import { Routes, Route, Navigate } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import SignupPage from "./pages/SignupPage";
import DashboardPage from "./pages/DashboardPage";
import { api } from "./api";
import { BG, PANEL, BORDER, TEXT_MUTED, ACCENT } from "./styles";
import type { User } from "./types";

function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const tokenData = await api.login(form);
      api.setToken(tokenData.access_token);
      const user = await api.me();
      onLogin(user);
    } catch (e: any) {
      setError(e.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: BG, color: "#F2F3F5", fontFamily: "'Inter', sans-serif" }}>
      <div style={{ background: PANEL, border: `1px solid ${BORDER}`, borderRadius: 16, padding: 32, width: 320, textAlign: "center" }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}><div style={{ background: "#242A33", padding: 12, borderRadius: 12, color: ACCENT }}><Lock size={24} /></div></div>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Welcome Back</h2>
        <p style={{ color: TEXT_MUTED, fontSize: 13, marginBottom: 24 }}>Enter your credentials to access Ops Copilot</p>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input type="text" placeholder="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} style={{ background: BG, border: `1px solid ${BORDER}`, color: "#F2F3F5", padding: "10px 12px", borderRadius: 8, fontSize: 14 }} />
          <input type="password" placeholder="Password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} style={{ background: BG, border: `1px solid ${BORDER}`, color: "#F2F3F5", padding: "10px 12px", borderRadius: 8, fontSize: 14 }} />
          {error && <div style={{ color: "#C4573F", fontSize: 12, textAlign: "left" }}>{error}</div>}
          <button disabled={loading} style={{ background: ACCENT, color: BG, border: "none", padding: "12px", borderRadius: 8, fontWeight: 600, cursor: "pointer", fontSize: 14 }}>{loading ? "Authenticating..." : "Login"}</button>
        </form>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // Session is now handled in-memory; no automatic restoration from localStorage
  }, []);

  const handleLogin = (u: User) => setUser(u);
  const handleLogout = () => {
    api.logout();
    setUser(null);
  };

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/login" element={!user ? <Login onLogin={handleLogin} /> : <Navigate to="/dashboard" />} />
      <Route
        path="/dashboard"
        element={
          user ? <DashboardPage user={user} onLogout={handleLogout} /> : <Navigate to="/login" />
        }
      />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}
