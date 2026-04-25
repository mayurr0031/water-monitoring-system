import "./WeatherPanel.css";

const fmt = (v, d = 1) => (v != null ? Number(v).toFixed(d) : "—");

function WItem({ value, unit, label }) {
  return (
    <div className="w-item">
      <div className="w-val">
        {value}<small> {unit}</small>
      </div>
      <div className="label">{label}</div>
    </div>
  );
}

export default function WeatherPanel({ weather }) {
  return (
    <div className="card weather-card">
      <div className="section-header" style={{ margin: "0 0 16px" }}>
        <span className="section-title">Weather</span>
        <div className="section-line" />
      </div>

      <div className="weather-grid">
        <WItem value={fmt(weather?.rain_mm)}    unit="mm"  label="Rainfall" />
        <WItem value={fmt(weather?.rain_hour)}  unit="%"   label="Rain Probability" />
        <WItem value={fmt(weather?.temperature)} unit="°C"  label="Temperature" />
        <WItem value={fmt(weather?.humidity)}   unit="%"   label="Humidity" />
      </div>
    </div>
  );
}
