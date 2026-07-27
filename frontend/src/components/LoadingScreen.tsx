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
      fontFamily: "'Inter', sans-serif"
    }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
        <div className="spinner" style={{
          width: 24,
          height: 24,
          border: "3px solid #2A2F38",
          borderTop: "3px solid #D4A24C",
          borderRadius: "50%",
          animation: "spin 1s linear infinite"
        }} />
        <span style={{ fontSize: 14, fontWeight: 500 }}>{message}</span>
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
