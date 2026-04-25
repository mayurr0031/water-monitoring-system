import "./Header.css";

export default function Header({ online, lastUpdate, onReset }) {
  const timeStr = lastUpdate
    ? lastUpdate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : "—";

  return (
    <header className="header">
      <div className="header-logo">
        <div className="logo-mark">
          <span className="logo-wave">〜</span>
        </div>
        <div>
          <h1 className="logo-title">FLOODWATCH</h1>
          <p className="logo-sub">IoT Flood Monitoring System</p>
        </div>
      </div>

      <div className="header-right">
        <div className={`status-pill ${online ? "online" : "offline"}`}>
          <span className="status-dot" />
          <span>{online ? "Live" : "Offline"}</span>
        </div>

        <span className="update-time">
          {lastUpdate ? `Updated ${timeStr}` : "Connecting…"}
        </span>

        <button className="reset-btn" onClick={onReset}>
          <span>⚠</span> Reset DB
        </button>
      </div>
    </header>
  );
}
