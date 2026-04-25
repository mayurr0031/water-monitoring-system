import "./AlertBanner.css";

const MESSAGES = {
  FLOOD: "🚨 FLOOD RISK DETECTED — Water levels critical. Immediate action required.",
  BLOCKAGE: "⚡ BLOCKAGE DETECTED — Significant differential between nodes. Inspect drainage.",
};

export default function AlertBanner({ condition }) {
  if (!condition || condition === "NORMAL") return null;

  return (
    <div className={`alert-banner alert-${condition.toLowerCase()}`}>
      <span className="alert-icon">{condition === "FLOOD" ? "▲" : "◆"}</span>
      {MESSAGES[condition] ?? `${condition} condition detected.`}
    </div>
  );
}
