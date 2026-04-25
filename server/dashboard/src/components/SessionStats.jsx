import "./SessionStats.css";

const fmt = (v, d = 1) => (v != null ? Number(v).toFixed(d) : "—");

function StatRow({ label, value }) {
  return (
    <div className="stat-row">
      <span className="stat-lbl">{label}</span>
      <span className="stat-val">{value}</span>
    </div>
  );
}

export default function SessionStats({ count, peak1, peak2, avgRR, lastPrediction }) {
  return (
    <div className="card stats-card">
      <div className="section-header" style={{ margin: "0 0 14px" }}>
        <span className="section-title">Session Stats</span>
        <div className="section-line" />
      </div>

      <StatRow label="Readings Received"   value={count} />
      <StatRow label="Node 1 Peak Level"   value={`${fmt(peak1)} cm`} />
      <StatRow label="Node 2 Peak Level"   value={`${fmt(peak2)} cm`} />
      <StatRow label="Avg Rise Rate N1"    value={`${fmt(avgRR, 4)} cm/s`} />
      <StatRow label="Last Prediction"     value={lastPrediction ?? "—"} />
    </div>
  );
}
