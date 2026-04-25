import "./ConditionHero.css";

const fmt = (v, d = 1) => (v != null ? Number(v).toFixed(d) : "—");

const STATE = {
  NORMAL:   { cls: "state-normal",   icon: "✓", label: "NORMAL" },
  FLOOD:    { cls: "state-flood",    icon: "▲", label: "FLOOD" },
  BLOCKAGE: { cls: "state-blockage", icon: "◆", label: "BLOCKAGE" },
};

export default function ConditionHero({ prediction }) {
  const key = prediction?.condition_label ?? "NORMAL";
  const s = STATE[key] ?? STATE.NORMAL;

  const fp = prediction ? fmt(prediction.flood_probability * 100) : "—";
  const bp = prediction ? fmt(prediction.blockage_probability * 100) : "—";

  return (
    <div className={`condition-card card ${s.cls}`}>
      <p className="label">System Condition</p>

      <div className="condition-icon">{s.icon}</div>
      <div className="condition-badge">{s.label}</div>

      <div className="prob-row">
        <div className="prob-item">
          <div className="prob-val flood-col">{fp}%</div>
          <div className="label">Flood Risk</div>
        </div>
        <div className="prob-divider" />
        <div className="prob-item">
          <div className="prob-val warn-col">{bp}%</div>
          <div className="label">Blockage Risk</div>
        </div>
      </div>

      <div className="ml-tag">
        {prediction?.ml_label
          ? `ML: ${prediction.ml_label}`
          : "ML: —"}
      </div>
    </div>
  );
}
