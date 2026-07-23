import React, { useState } from "react";
import { UserPlus } from "lucide-react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api";

const BG = "#14171C";
const PANEL = "#1B1F26";
const BORDER = "#2A2F38";
const ACCENT = "#D4A24C";
const TEXT_MUTED = "#8891A0";

export default function SignupPage() {
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.signup(form);
      // After successful signup, navigate to login
      navigate("/login");
    } catch (e: any) {
      setError(e.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

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
            <UserPlus size={24} />
          </div>
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Create Account</h2>
        <p style={{ color: TEXT_MUTED, fontSize: 13, marginBottom: 24 }}>Join Ops Copilot to automate your delivery ops</p>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input
            type="text"
            placeholder="Username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            style={{ background: BG, border: `1px solid ${BORDER}`, color: "#F2F3F5", padding: "10px 12px", borderRadius: 8, fontSize: 14 }}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            style={{ background: BG, border: `1px solid ${BORDER}`, color: "#F2F3F5", padding: "10px 12px", borderRadius: 8, fontSize: 14 }}
            required
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
            {loading ? "Creating account..." : "Sign Up"}
          </button>
        </form>
        <div style={{ marginTop: 24, fontSize: 13, color: TEXT_MUTED }}>
          Already have an account?{" "}
          <Link to="/login" style={{ color: ACCENT, textDecoration: "none", fontWeight: 600 }}>Sign in</Link>
        </div>
      </div>
    </div>
  );
}
