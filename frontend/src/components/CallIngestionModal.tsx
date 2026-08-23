import { useState, useEffect } from "react";
import { api } from "../api";
import {
  ACCENT, BG, PANEL, BORDER, TEXT_LIGHT, TEXT_MUTED, OK, RED
} from "../styles";
import type { Agent } from "../types";
import { Upload, X, FileText, Music, AlertCircle, CheckCircle2 } from "lucide-react";

interface CallIngestionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CallIngestionModal({ isOpen, onClose }: CallIngestionModalProps) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState("");
  const [customerRef, setCustomerRef] = useState("");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [transcript, setTranscript] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

  useEffect(() => {
    if (isOpen) {
      api.listAgents().then(setAgents).catch(console.error);
    }
  }, [isOpen]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedAgent) {
      setStatus({ type: "error", message: "Please select an agent" });
      return;
    }
    if (!audioFile && !transcript) {
      setStatus({ type: "error", message: "Provide either an audio file or a transcript" });
      return;
    }

    setLoading(true);
    setStatus(null);

    try {
      const formData = new FormData();
      formData.append("agent_id", selectedAgent);
      if (customerRef) formData.append("customer_ref", customerRef);
      if (audioFile) formData.append("audio", audioFile);
      if (transcript) formData.append("transcript", transcript);

      await api.uploadCall(formData);
      setStatus({ type: "success", message: "Call uploaded successfully! Processing has started." });

      // Reset form after success
      setTimeout(() => {
        setAudioFile(null);
        setTranscript("");
        setCustomerRef("");
        setSelectedAgent("");
      }, 2000);
    } catch (e: any) {
      setStatus({ type: "error", message: e.message || "An error occurred during upload" });
    } finally {
      setLoading(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
      zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center",
      background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)"
    }}>
      <div style={{
        background: PANEL, border: `1px solid ${BORDER}`, borderRadius: 16,
        width: "500px", maxWidth: "90%", position: "relative",
        boxShadow: "0 20px 40px rgba(0,0,0,0.4)",
        overflow: "hidden", display: "flex", flexDirection: "column"
      }}>
        <div style={{ padding: "20px 24px", borderBottom: `1px solid ${BORDER}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: TEXT_LIGHT, margin: 0 }}>Ingest New Call</h2>
          <button onClick={onClose} style={{ background: "transparent", border: 0, cursor: "pointer", color: TEXT_MUTED }}><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: "24px", display: "flex", flexDirection: "column", gap: 20 }}>
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: TEXT_MUTED, marginBottom: 8, textTransform: "uppercase" }}>Agent</label>
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              style={{
                width: "100%", padding: "10px 12px", borderRadius: 8,
                background: BG, border: `1px solid ${BORDER}`, color: TEXT_LIGHT, fontSize: 14, cursor: "pointer"
              }}
            >
              <option value="">Select Agent...</option>
              {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>

          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: TEXT_MUTED, marginBottom: 8, textTransform: "uppercase" }}>Customer Reference (Optional)</label>
            <input
              type="text"
              value={customerRef}
              onChange={(e) => setCustomerRef(e.target.value)}
              placeholder="e.g. CUST-12345"
              style={{
                width: "100%", padding: "10px 12px", borderRadius: 8,
                background: BG, border: `1px solid ${BORDER}`, color: TEXT_LIGHT, fontSize: 14, boxSizing: "border-box"
              }}
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 16, padding: "16px", borderRadius: 12, background: BG, border: `1px solid ${BORDER}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, fontWeight: 600, color: TEXT_LIGHT }}>
              <Music size={16} color={ACCENT} /> Audio File
            </div>
            <div style={{
              border: `2px dashed ${BORDER}`, borderRadius: 8, padding: "20px",
              textAlign: "center", cursor: "pointer", position: "relative",
              transition: "border-color 0.2s",
              background: audioFile ? "rgba(212, 162, 76, 0.05)" : "transparent"
            }}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (e.dataTransfer.files && e.dataTransfer.files[0]) setAudioFile(e.dataTransfer.files[0]);
            }}>
              <input
                type="file"
                accept="audio/*"
                onChange={(e) => e.target.files && setAudioFile(e.target.files[0])}
                style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", opacity: 0, cursor: "pointer" }}
              />
              <Upload size={24} color={TEXT_MUTED} style={{ marginBottom: 8 }} />
              <div style={{ fontSize: 13, color: TEXT_MUTED }}>{audioFile ? audioFile.name : "Drag & drop audio or click to upload"}</div>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 16, padding: "16px", borderRadius: 12, background: BG, border: `1px solid ${BORDER}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, fontWeight: 600, color: TEXT_LIGHT }}>
              <FileText size={16} color={ACCENT} /> Transcript
            </div>
            <textarea
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Paste the call transcript here..."
              style={{
                width: "100%", height: 100, padding: "10px 12px", borderRadius: 8,
                background: PANEL, border: `1px solid ${BORDER}`, color: TEXT_LIGHT, fontSize: 14, resize: "none", boxSizing: "border-box"
              }}
            />
          </div>

          {status && (
            <div style={{
              display: "flex", alignItems: "center", gap: 8, padding: "12px", borderRadius: 8,
              background: status.type === "success" ? "rgba(0, 255, 0, 0.05)" : "rgba(255, 0, 0, 0.05)",
              border: `1px solid ${status.type === "success" ? OK : RED}`,
              color: status.type === "success" ? OK : RED,
              fontSize: 13, fontWeight: 500
            }}>
              {status.type === "success" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
              {status.message}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              background: ACCENT, color: BG, border: "none", padding: "12px",
              borderRadius: 8, fontWeight: 700, cursor: loading ? "not-allowed" : "pointer",
              fontSize: 14, transition: "opacity 0.2s", opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? "Uploading..." : "Start Auto-QA Pipeline"}
          </button>
        </form>
      </div>
    </div>
  );
}
