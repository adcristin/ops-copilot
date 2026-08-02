import React, { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";

const BG = "#14171C";
const PANEL = "#1B1F26";
const BORDER = "#2A2F38";
const ACCENT = "#D4A24C";
const TEXT_MUTED = "#8891A0";

export default function AuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      api.setToken(token);
      navigate("/dashboard");
    } else {
      navigate("/login");
    }
  }, [searchParams, navigate]);

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
            <div className="spinner" style={{ width: 24, height: 24, border: "3px solid #2A2F38", borderTop: `3px solid ${ACCENT}`, borderRadius: "50%", animation: "spin 1s linear infinite" }} />
          </div>
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Authenticating...</h2>
        <p style={{ color: TEXT_MUTED, fontSize: 13 }}>Please wait while we sign you in</p>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    </div>
  );
}
