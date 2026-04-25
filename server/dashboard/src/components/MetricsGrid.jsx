import "./MetricsGrid.css";

const fmt = (v, d = 1) => (v != null ? Number(v).toFixed(d) : "—");

function MetricCard({ tag, value, unit, sub, pct, extraLabel }) {
  return (
    <div className="metric-card card">
      <p className="label metric-tag">{tag}</p>
      <div className="metric-value">
        <span className="metric-number">{value}</span>
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
      {sub && <p className="metric-sub">{sub}</p>}
      {pct != null && (
        <>
          <div className="pbar-bg">
            <div
              className="pbar-fill"
              style={{ width: `${Math.min(pct, 100)}%` }}
            />
          </div>
          <p className="metric-sub">{fmt(pct)}% filled</p>
        </>
      )}
      {extraLabel && <p className="metric-extra">{extraLabel}</p>}
    </div>
  );
}

export default function MetricsGrid({ device1, device2, levelDiff }) {
  const rr2 = device2 ? fmt(device2.rise_rate, 3) : "—";

  return (
    <div className="metrics-grid">
      <MetricCard
        tag="Node 1 · Upstream"
        value={device1 ? fmt(device1.water_level) : "—"}
        unit="cm"
        sub="Water Level"
        pct={device1?.percentage}
      />
      <MetricCard
        tag="Node 2 · Downstream"
        value={device2 ? fmt(device2.water_level) : "—"}
        unit="cm"
        sub="Water Level"
        pct={device2?.percentage}
      />
      <MetricCard
        tag="Rise Rate"
        value={device1 ? fmt(device1.rise_rate, 3) : "—"}
        unit="cm/s"
        sub={`Node 1 rate`}
        extraLabel={`Node 2: ${rr2} cm/s`}
      />
      <MetricCard
        tag="Level Differential"
        value={levelDiff != null ? fmt(levelDiff) : "—"}
        unit="cm"
        sub="Between Node 1 & 2"
      />
    </div>
  );
}
