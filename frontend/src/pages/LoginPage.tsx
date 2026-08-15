import React, { useState, useEffect } from "react";
import { Lock } from "lucide-react";
import { useNavigate, Link } from "react-router-dom";
import { api, API_BASE } from "../api";
import SocialButton from "../components/SocialButton";
import { LoadingScreen } from "../components/LoadingScreen";

const BG = "#14171C";
const PANEL = "#1B1F26";
const BORDER = "#2A2F38";
const ACCENT = "#D4A24C";
const TEXT_MUTED = "#8891A0";

export default function LoginPage() {
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showColdStart, setShowColdStart] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (loading) {
      timer = setTimeout(() => setShowColdStart(true), 2000);
    } else {
      setShowColdStart(false);
    }
    return () => clearTimeout(timer);
  }, [loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const tokenData = await api.login(form);
      api.setToken(tokenData.access_token);
      navigate("/dashboard");
    } catch (e: any) {
      setError(e.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const oauthLogin = (provider: string) => {
    window.location.href = `${API_BASE}/auth/login/${provider}`;
  };

  if (showColdStart) {
    return <LoadingScreen message="Waking up the server, this can take up to a minute..." />;
  }

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      background: BG,
      color: "#F2F3F5",
      fontFamily: "'Inter', sans-serif"
    }}>
      <div style={{
        background: PANEL,
        border: `1px solid ${BORDER}`,
        borderRadius: 16,
        padding: 32,
        width: 320,
        textAlign: "center"
      }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}>
          <div style={{ background: "#242A33", padding: 12, borderRadius: 12, color: ACCENT }}>
            <Lock size={24} />
          </div>
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Welcome Back</h2>
        <p style={{ color: TEXT_MUTED, fontSize: 13, marginBottom: 24 }}>Enter your credentials to access Ops Copilot</p>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input
            type="text"
            placeholder="Email or Username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            style={{ background: BG, border: `1px solid ${BORDER}`, color: "#F2F3F5", padding: "10px 12px", borderRadius: 8, fontSize: 14 }}
          />
          <input
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            style={{ background: BG, border: `1px solid ${BORDER}`, color: "#F2F3F5", padding: "10px 12px", borderRadius: 8, fontSize: 14 }}
          />
          {error && <div style={{ color: "#C4573F", fontSize: 12, textAlign: "left" }}>{error}</div>}
          <button
            disabled={loading}
            style={{
              background: ACCENT,
              color: BG,
              border: "none",
              padding: "12px",
              borderRadius: 8,
              fontWeight: 600,
              cursor: "pointer",
              fontSize: 14
            }}
          >
            {loading ? "Authenticating..." : "Login"}
          </button>
        </form>

        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 24 }}>
          <div style={{ height: 1, background: BORDER, opacity: 0.5 }} />
          <p style={{ color: TEXT_MUTED, fontSize: 12 }}>Or continue with</p>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <SocialButton
              provider="google"
              onClick={() => oauthLogin("google")}
              label="LOGIN WITH GOOGLE"
            />
            <SocialButton
              provider="github"
              onClick={() => oauthLogin("github")}
              label="LOGIN WITH GITHUB"
            />
          </div>
        </div>

        <div style={{ marginTop: 24, fontSize: 13, color: TEXT_MUTED }}>
          Don't have an account?{" "}
          <Link to="/signup" style={{ color: ACCENT, textDecoration: "none", fontWeight: 600 }}>Sign up</Link>
        </div>
      </div>
    </div>
  );
}
