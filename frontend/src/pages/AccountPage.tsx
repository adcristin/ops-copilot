import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { User } from "../types";
import { api } from "../api";
import {
  ACCENT, BG, PANEL, BORDER, TEXT_MUTED, TEXT_LIGHT, RED, DARK_PANEL
} from "../styles";
import { User as UserIcon, Lock, Save, AlertCircle, CheckCircle } from "lucide-react";

export default function AccountPage({ user: initialUser, onLogout }: { user: User; onLogout: () => void }) {
  const [user, setUser] = useState<User>(initialUser);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const navigate = useNavigate();

  // Profile form state
  const [profileForm, setProfileForm] = useState({
    username: initialUser.username,
    email: initialUser.email || "",
  });

  // Password form state
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  useEffect(() => {
    api.me().then(setUser).catch(console.error);
  }, []);

  async function handleUpdateProfile() {
    setLoading(true);
    setMessage(null);
    try {
      const updatedUser = await api.updateProfile(profileForm);
      setUser(updatedUser);
      setMessage({ type: "success", text: "Profile updated successfully!" });
      setTimeout(() => {
        navigate("/dashboard");
      }, 1500);
    } catch (e: any) {
      setMessage({ type: "error", text: e.message || "Failed to update profile" });
    } finally {
      setLoading(false);
    }
  }

  async function handleChangePassword() {
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setMessage({ type: "error", text: "New passwords do not match" });
      return;
    }

    setLoading(true);
    setMessage(null);
    try {
      await api.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      setMessage({ type: "success", text: "Password changed successfully!" });
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
    } catch (e: any) {
      setMessage({ type: "error", text: e.message || "Failed to change password" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      display: "flex",
      height: "100vh",
      background: BG,
      fontFamily: "'Inter', -apple-system, sans-serif",
      color: TEXT_LIGHT,
      padding: "48px 32px",
      overflowY: "auto",
      boxSizing: "border-box"
    }}>
      <div style={{ maxWidth: 600, width: "100%", margin: "0 auto" }}>
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 28, fontWeight: 800, margin: 0 }}>Account Settings</h1>
          <p style={{ color: TEXT_MUTED, fontSize: 14, marginTop: 8 }}>Manage your profile and security preferences.</p>
        </div>

        {message && (
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "12px 16px",
            borderRadius: 8,
            marginBottom: 24,
            background: message.type === "success" ? "rgba(76, 154, 141, 0.1)" : "rgba(196, 87, 63, 0.1)",
            border: `1px solid ${message.type === "success" ? OK : RED}`,
            color: message.type === "success" ? OK : RED,
            fontSize: 14,
            fontWeight: 500
          }}>
            {message.type === "success" ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
            {message.text}
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Profile Section */}
          <div style={{ background: PANEL, border: `1px solid ${BORDER}`, borderRadius: 12, padding: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
              <UserIcon size={20} color={ACCENT} />
              <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>Profile Information</h2>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <label style={{ fontSize: 12, color: TEXT_MUTED, fontWeight: 500 }}>Username</label>
                <input
                  value={profileForm.username}
                  onChange={(e) => setProfileForm({ ...profileForm, username: e.target.value })}
                  style={{
                    background: DARK_PANEL,
                    border: `1px solid ${BORDER}`,
                    borderRadius: 6,
                    padding: "10px 12px",
                    color: TEXT_LIGHT,
                    fontSize: 14,
                    outline: "none"
                  }}
                />
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <label style={{ fontSize: 12, color: TEXT_MUTED, fontWeight: 500 }}>Email Address</label>
                <input
                  value={profileForm.email}
                  onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })}
                  style={{
                    background: DARK_PANEL,
                    border: `1px solid ${BORDER}`,
                    borderRadius: 6,
                    padding: "10px 12px",
                    color: TEXT_LIGHT,
                    fontSize: 14,
                    outline: "none"
                  }}
                />
              </div>

              <button
                onClick={handleUpdateProfile}
                disabled={loading}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  background: ACCENT,
                  color: BG,
                  border: "none",
                  padding: "12px",
                  borderRadius: 8,
                  fontWeight: 600,
                  cursor: loading ? "not-allowed" : "pointer",
                  fontSize: 14,
                  marginTop: 8,
                  opacity: loading ? 0.7 : 1
                }}
              >
                <Save size={16} /> {loading ? "Saving..." : "Save Profile"}
              </button>
            </div>
          </div>

          {/* Security Section */}
          <div style={{ background: PANEL, border: `1px solid ${BORDER}`, borderRadius: 12, padding: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
              <Lock size={20} color={ACCENT} />
              <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>Security Settings</h2>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <label style={{ fontSize: 12, color: TEXT_MUTED, fontWeight: 500 }}>Current Password</label>
                <input
                  type="password"
                  value={passwordForm.current_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                  style={{
                    background: DARK_PANEL,
                    border: `1px solid ${BORDER}`,
                    borderRadius: 6,
                    padding: "10px 12px",
                    color: TEXT_LIGHT,
                    fontSize: 14,
                    outline: "none"
                  }}
                />
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <label style={{ fontSize: 12, color: TEXT_MUTED, fontWeight: 500 }}>New Password</label>
                <input
                  type="password"
                  value={passwordForm.new_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                  style={{
                    background: DARK_PANEL,
                    border: `1px solid ${BORDER}`,
                    borderRadius: 6,
                    padding: "10px 12px",
                    color: TEXT_LIGHT,
                    fontSize: 14,
                    outline: "none"
                  }}
                />
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <label style={{ fontSize: 12, color: TEXT_MUTED, fontWeight: 500 }}>Confirm New Password</label>
                <input
                  type="password"
                  value={passwordForm.confirm_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                  style={{
                    background: DARK_PANEL,
                    border: `1px solid ${BORDER}`,
                    borderRadius: 6,
                    padding: "10px 12px",
                    color: TEXT_LIGHT,
                    fontSize: 14,
                    outline: "none"
                  }}
                />
              </div>

              <button
                onClick={handleChangePassword}
                disabled={loading}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  background: ACCENT,
                  color: BG,
                  border: "none",
                  padding: "12px",
                  borderRadius: 8,
                  fontWeight: 600,
                  cursor: loading ? "not-allowed" : "pointer",
                  fontSize: 14,
                  marginTop: 8,
                  opacity: loading ? 0.7 : 1
                }}
              >
                <Lock size={16} /> {loading ? "Updating..." : "Update Password"}
              </button>
            </div>
          </div>

          {/* Session Section */}
          <div style={{ background: PANEL, border: `1px solid ${BORDER}`, borderRadius: 12, padding: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
              <UserIcon size={20} color={ACCENT} />
              <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>Session Management</h2>
            </div>
            <button
              onClick={onLogout}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                background: "transparent",
                color: RED,
                border: `1px solid ${RED}`,
                padding: "12px",
                borderRadius: 8,
                fontWeight: 600,
                cursor: "pointer",
                fontSize: 14,
                width: "100%"
              }}
            >
              Logout of Account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
