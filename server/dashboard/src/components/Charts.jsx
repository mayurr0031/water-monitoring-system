import { useEffect, useRef } from "react";
import "./Charts.css";

const CHART_BASE = {
  animation: false,
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        color: "#4a5568",
        font: { size: 11, family: "'JetBrains Mono', monospace" },
        boxWidth: 24,
        padding: 16,
      },
    },
  },
  scales: {
    x: {
      ticks: {
        color: "#4a5568",
        maxTicksLimit: 7,
        font: { size: 10, family: "'JetBrains Mono', monospace" },
      },
      grid: { color: "#1f2633" },
    },
    y: {
      ticks: {
        color: "#4a5568",
        font: { size: 10, family: "'JetBrains Mono', monospace" },
      },
      grid: { color: "#1f2633" },
    },
  },
};

function useChart(ref, config) {
  const chartRef = useRef(null);

  useEffect(() => {
    if (!ref.current || !window.Chart) return;
    if (chartRef.current) chartRef.current.destroy();
    chartRef.current = new window.Chart(ref.current, config);
    return () => {
      chartRef.current?.destroy();
      chartRef.current = null;
    };
    // eslint-disable-next-line
  }, []);

  return chartRef;
}

export default function Charts({ history }) {
  const levelRef = useRef(null);
  const rateRef = useRef(null);
  const levelChart = useRef(null);
  const rateChart = useRef(null);

  // Init charts once Chart.js is available
  useEffect(() => {
    const init = () => {
      if (!window.Chart) return;

      if (levelRef.current && !levelChart.current) {
        levelChart.current = new window.Chart(levelRef.current, {
          type: "line",
          data: {
            labels: [],
            datasets: [
              {
                label: "Node 1",
                data: [],
                borderColor: "#00d4ff",
                backgroundColor: "rgba(0,212,255,0.07)",
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.35,
                fill: true,
              },
              {
                label: "Node 2",
                data: [],
                borderColor: "#00e5a0",
                backgroundColor: "rgba(0,229,160,0.07)",
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.35,
                fill: true,
              },
            ],
          },
          options: CHART_BASE,
        });
      }

      if (rateRef.current && !rateChart.current) {
        rateChart.current = new window.Chart(rateRef.current, {
          type: "line",
          data: {
            labels: [],
            datasets: [
              {
                label: "Node 1",
                data: [],
                borderColor: "#f5a623",
                backgroundColor: "rgba(245,166,35,0.07)",
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.35,
                fill: true,
              },
              {
                label: "Node 2",
                data: [],
                borderColor: "#ff3d57",
                backgroundColor: "rgba(255,61,87,0.07)",
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.35,
                fill: true,
              },
            ],
          },
          options: CHART_BASE,
        });
      }
    };

    // Retry if Chart.js not loaded yet
    if (window.Chart) {
      init();
    } else {
      const id = setInterval(() => {
        if (window.Chart) { init(); clearInterval(id); }
      }, 200);
      return () => clearInterval(id);
    }
  }, []);

  // Update chart data when history changes
  useEffect(() => {
    const { d1, d2 } = history;
    const labels = d1.length >= d2.length
      ? d1.map((r) => r.ts)
      : d2.map((r) => r.ts);

    if (levelChart.current) {
      levelChart.current.data.labels = labels;
      levelChart.current.data.datasets[0].data = d1.map((r) => r.wl);
      levelChart.current.data.datasets[1].data = d2.map((r) => r.wl);
      levelChart.current.update("none");
    }

    if (rateChart.current) {
      rateChart.current.data.labels = labels;
      rateChart.current.data.datasets[0].data = d1.map((r) => r.rr);
      rateChart.current.data.datasets[1].data = d2.map((r) => r.rr);
      rateChart.current.update("none");
    }
  }, [history]);

  return (
    <>
      <div className="section-header">
        <span className="section-title">Water Level Trends</span>
        <div className="section-line" />
      </div>

      <div className="charts-grid">
        <div className="chart-card card">
          <p className="chart-title label">Water Level Over Time (cm)</p>
          <div className="chart-wrap">
            <canvas ref={levelRef} />
          </div>
        </div>
        <div className="chart-card card">
          <p className="chart-title label">Rise Rate (cm/s)</p>
          <div className="chart-wrap">
            <canvas ref={rateRef} />
          </div>
        </div>
      </div>
    </>
  );
}
