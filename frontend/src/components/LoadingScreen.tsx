const BG = "#14171C";
const TEXT_MUTED = "#8891A0";

export const LoadingScreen = ({ message = "Loading user profile..." }) => {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      background: BG,
      color: TEXT_MUTED,
      fontFamily: "'Inter', sans-serif",
      transition: "opacity 0.3s ease"
    }}>
      <div style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 20,
        padding: "0 20px",
        textAlign: "center"
      }}>
        <div className="spinner" style={{
          width: 32,
          height: 32,
          border: "3px solid #2A2F38",
          borderTop: "3px solid #D4A24C",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite"
        }} />
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <span style={{ fontSize: 15, fontWeight: 500, color: "#F2F3F5" }}>{message}</span>
          <span style={{ fontSize: 12, opacity: 0.6 }}>Please hold on, we're getting things ready.</span>
        </div>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    </div>
  );
};
