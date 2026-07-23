import React from "react";
import { Github, ArrowRight, CheckCircle2, Zap, ShieldCheck, LayoutDashboard } from "lucide-react";
import { useNavigate } from "react-router-dom";

const ACCENT = "#D4A24C";
const OK = "#4C9A8D";
const BG = "#14171C";
const PANEL = "#1B1F26";
const BORDER = "#2A2F38";
const TEXT_MUTED = "#8891A0";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div style={{
      background: BG,
      color: "#F2F3F5",
      fontFamily: "'Inter', sans-serif",
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column"
    }}>
      {/* Header */}
      <header style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "24px 40px",
        maxWidth: 1200,
        width: "100%",
        margin: "0 auto"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 14,
            color: ACCENT,
            fontWeight: 600
          }}>
            OPS://Copilot
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: TEXT_MUTED, transition: "color 0.2s" }}
            onMouseOver={(e) => e.currentTarget.style.color = "#F2F3F5"}
            onMouseOut={(e) => e.currentTarget.style.color = TEXT_MUTED}
          >
            <Github size={20} />
          </a>
          <button
            onClick={() => navigate("/login")}
            style={{
              background: "transparent",
              border: `1px solid ${BORDER}`,
              color: "#F2F3F5",
              padding: "8px 16px",
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 500,
              cursor: "pointer",
              transition: "background 0.2s"
            }}
            onMouseOver={(e) => e.currentTarget.style.background = PANEL}
            onMouseOut={(e) => e.currentTarget.style.background = "transparent"}
          >
            Sign In
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 40px",
        textAlign: "center",
        maxWidth: 1200,
        width: "100%",
        margin: "0 auto"
      }}>
        <div style={{
          background: "radial-gradient(circle at center, #242A33 0%, transparent 70%)",
          position: "absolute",
          width: 600,
          height: 600,
          borderRadius: "50%",
          zIndex: 0,
          pointerEvents: "none"
        }} />

        <div style={{ position: "relative", zIndex: 1 }}>
          <h1 style={{
            fontSize: 64,
            fontWeight: 800,
            letterSpacing: -2,
            marginBottom: 24,
            lineHeight: 1.1
          }}>
            Ops <span style={{ color: ACCENT }}>Copilot</span>
          </h1>
          <p style={{
            fontSize: 20,
            color: TEXT_MUTED,
            maxWidth: 600,
            margin: "0 auto 48px auto",
            lineHeight: 1.6
          }}>
            LLM-powered call QA, mailbox triage & task automation.
            Transform your delivery operations from reactive to proactive.
          </p>

          <button
            onClick={() => navigate("/signup")}
            style={{
              background: ACCENT,
              color: BG,
              border: "none",
              padding: "16px 32px",
              borderRadius: 12,
              fontSize: 16,
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 10,
              margin: "0 auto"
            }}
          >
            Get Started <ArrowRight size={20} />
          </button>
        </div>

        {/* Features */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 24,
          marginTop: 80,
          width: "100%",
          maxWidth: 1000
        }}>
          {[
            {
              icon: <Zap color={ACCENT} size={24} />,
              title: "AI Call Scoring",
              desc: "Automatic rubric-based scoring for every call with coaching notes."
            },
            {
              icon: <ShieldCheck color={OK} size={24} />,
              title: "Mailbox Triage",
              desc: "Intelligent classification and priority routing for customer escalations."
            },
            {
              icon: <LayoutDashboard color="#5B8FD9" size={24} />,
              title: "Task Automation",
              desc: "Instant task generation from QA flags and mailbox escalations."
            }
          ].map((feature, i) => (
            <div key={i} style={{
              background: PANEL,
              border: `1px solid ${BORDER}`,
              borderRadius: 16,
              padding: 24,
              textAlign: "left",
              transition: "transform 0.2s",
              cursor: "default"
            }}>
              <div style={{ marginBottom: 16 }}>{feature.icon}</div>
              <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{feature.title}</h3>
              <p style={{ fontSize: 14, color: TEXT_MUTED, lineHeight: 1.5 }}>{feature.desc}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
