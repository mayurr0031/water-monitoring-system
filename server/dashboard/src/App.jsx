import { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import ConditionHero from "./components/ConditionHero";
import MetricsGrid from "./components/MetricsGrid";
import Charts from "./components/Charts";
import WeatherPanel from "./components/WeatherPanel";
import SessionStats from "./components/SessionStats";
import AlertBanner from "./components/AlertBanner";
import "./index.css";

const API_BASE = "http://localhost:5000";
const POLL_INTERVAL = 5000;

export default function App() {
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState({ d1: [], d2: [] });
  const [online, setOnline] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [sessionStats, setSessionStats] = useState({
    count: 0,
    peak1: 0,
    peak2: 0,
    avgRR: [],
  });

  const fetchLatest = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/latest`);
      if (!res.ok) throw new Error(res.status);
      const data = await res.json();
      setLatest(data);
      setOnline(true);
      setLastUpdate(new Date());

      setSessionStats((prev) => {
        const d1 = data.device1;
        const d2 = data.device2;
        const newAvg = d1
          ? [...prev.avgRR.slice(-19), d1.rise_rate]
          : prev.avgRR;
        return {
          count: d1 ? prev.count + 1 : prev.count,
          peak1: d1 ? Math.max(prev.peak1, d1.water_level) : prev.peak1,
          peak2: d2 ? Math.max(prev.peak2, d2.water_level) : prev.peak2,
          avgRR: newAvg,
        };
      });

      setHistory((prev) => {
        const ts = new Date().toLocaleTimeString();
        const trim = (arr) => (arr.length >= 60 ? arr.slice(1) : arr);
        return {
          d1: data.device1
            ? trim([...prev.d1, { ts, wl: data.device1.water_level, rr: data.device1.rise_rate }])
            : prev.d1,
          d2: data.device2
            ? trim([...prev.d2, { ts, wl: data.device2.water_level, rr: data.device2.rise_rate }])
            : prev.d2,
        };
      });
    } catch {
      setOnline(false);
    }
  }, []);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/history?hours=1`);
        const { data } = await res.json();
        if (!data?.length) return;
        const d1 = data.filter((r) => r.device_id === 1);
        const d2 = data.filter((r) => r.device_id === 2);
        setHistory({
          d1: d1.map((r) => ({ ts: new Date(r.timestamp).toLocaleTimeString(), wl: r.water_level, rr: r.rise_rate })),
          d2: d2.map((r) => ({ ts: new Date(r.timestamp).toLocaleTimeString(), wl: r.water_level, rr: r.rise_rate })),
        });
      } catch {}
    };
    loadHistory();
    fetchLatest();
    const id = setInterval(fetchLatest, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [fetchLatest]);

  const handleReset = async () => {
    if (!confirm("Clear ALL stored data from the database? This cannot be undone.")) return;
    await fetch(`${API_BASE}/api/reset`, { method: "POST" });
    setHistory({ d1: [], d2: [] });
    setSessionStats({ count: 0, peak1: 0, peak2: 0, avgRR: [] });
    setLatest(null);
  };

  const condition = latest?.prediction?.condition_label ?? null;
  const avgRR = sessionStats.avgRR.length
    ? sessionStats.avgRR.reduce((a, b) => a + b, 0) / sessionStats.avgRR.length
    : 0;

  return (
    <div className="app">
      <div className="scanline" />
      <div className="wrapper">
        <Header online={online} lastUpdate={lastUpdate} onReset={handleReset} />
        <AlertBanner condition={condition} />
        <div className="hero-row">
          <ConditionHero prediction={latest?.prediction} />
          <MetricsGrid
            device1={latest?.device1}
            device2={latest?.device2}
            levelDiff={latest?.level_difference}
          />
        </div>
        <Charts history={history} />
        <div className="bottom-row">
          <WeatherPanel weather={latest?.weather} />
          <SessionStats
            count={sessionStats.count}
            peak1={sessionStats.peak1}
            peak2={sessionStats.peak2}
            avgRR={avgRR}
            lastPrediction={latest?.prediction?.condition_label}
          />
        </div>
      </div>
    </div>
  );
}
