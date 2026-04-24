# 🌊 FloodWatch — IoT Flood Monitoring System

Real-time flood and drainage-blockage detection using ESP32 ultrasonic sensors, a Flask backend, MySQL database, and a RandomForest ML model.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Hardware Layer                           │
│  ┌─────────────┐         ┌─────────────┐                    │
│  │  Node 1     │         │  Node 2     │                    │
│  │  ESP32      │         │  ESP32      │                    │
│  │  HC-SR04    │         │  HC-SR04    │                    │
│  │ (Upstream)  │         │(Downstream) │                    │
│  └──────┬──────┘         └──────┬──────┘                    │
│         │  POST /api/water-level│                           │
└─────────┼─────────────────────  ┼────────────────────────── ┘
          │         WiFi          │
          ▼                       ▼
┌──────────────────────────────────────────────────────────────┐
│                   Flask Server (app.py)                      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Sensor Data  │  │  ML Model    │  │  Weather API     │  │
│  │ Ingestion    │  │ (RF + Rules) │  │  (Tomorrow.io)   │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │            │
│         ▼                 ▼                    ▼            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              MySQL Database                         │    │
│  │   sensor_readings | predictions | weather_data      │    │
│  └──────────────────────────┬──────────────────────────┘    │
└─────────────────────────────┼────────────────────────────── ┘
                              │
                              ▼
                   ┌──────────────────┐
                   │  dashboard.html  │
                   │  (Chart.js UI)   │
                   │  Auto-refresh 5s │
                   └──────────────────┘
```

---

## Features

- **Dual-node sensing** — Two ESP32 + HC-SR04 sensors at upstream and downstream points
- **Rule-based + ML hybrid prediction** — Rules take priority; RandomForest supplements when NORMAL
- **Real-time dashboard** — Auto-refreshing Chart.js UI with live water level, rise rate, and condition badge
- **Weather integration** — Tomorrow.io API (fallback to dummy values when no key)
- **MySQL persistence** — Three tables: `sensor_readings`, `predictions`, `weather_data`
- **Thread-safe** — All DB operations protected by a threading Lock
- **Environment-configured** — All secrets in `.env`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/water-level` | Receive ESP32 sensor JSON |
| GET | `/api/latest` | Latest readings + prediction + weather |
| GET | `/api/history?hours=N&device_id=N` | Historical sensor data |
| GET | `/api/predict` | On-demand prediction (fetches live weather) |
| GET | `/api/weather` | Fetch + store fresh weather data |
| GET | `/api/device/<id>/stats` | Per-device statistics |
| POST | `/api/reset` | Clear all DB data |
| GET | `/` | Serve dashboard |

---

## ESP32 JSON Payload

```json
{
  "device_id": 1,
  "water_level": 12.50,
  "rise_rate": 0.0312,
  "percentage": 31.25
}
```

---

## ML Model

- **Algorithm**: RandomForestClassifier (200 estimators, balanced class weights)
- **Features**: `water_level_node1`, `water_level_node2`, `level_diff`, `rise_rate_node1`, `rise_rate_node2`, `rain_hour`, `rain_intensity`
- **Labels**: `normal` (0) · `blockage` (1) · `flood` (2) *(LabelEncoder alphabetical order)*
- **Rule overrides**:
  - Either node > 35 cm → **FLOOD**
  - Both nodes > 30 cm → **FLOOD**
  - Differential > 15 cm → **BLOCKAGE**
  - Node1 rise > 2 cm/s AND Node2 rise < 0.5 → **BLOCKAGE**

---

## Folder Structure

```
project/
├── HC-SR04/
│   ├── platformio.ini
│   └── src/
│       └── main.cpp
│   └── lib/
│       └── WaterLevel/
│           ├── WaterLevel.h
│           └── WaterLevel.cpp
└── server/
    ├── app.py
    ├── dashboard.html
    ├── requirements.txt
    ├── model.joblib
    ├── encoder.joblib
    ├── .env
    ├── README.md
    └── SETUP.md
```

---

## Screenshots

> Dashboard — Normal State
> ![Normal](placeholder-normal.png)

> Dashboard — Flood Alert
> ![Flood](placeholder-flood.png)