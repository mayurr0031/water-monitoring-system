"""
IoT Flood Monitoring System - Flask Backend
Fixed & Production-Ready
"""

import logging
import os
from datetime import datetime, timedelta
from threading import Lock

import joblib
import mysql.connector
import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from mysql.connector import Error

# ─────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

app = Flask(__name__, template_folder=".", static_folder=".")
CORS(app)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "water_level_monitor"),
}

TOMORROW_API_KEY = os.getenv("TOMORROW_API_KEY", '')
TOMORROW_API_URL = "https://api.tomorrow.io/v4/weather/realtime"
LOCATION_LAT = os.getenv("LOCATION_LAT", "28.7041")
LOCATION_LON = os.getenv("LOCATION_LON", "77.1025")

# ML feature order — MUST match training notebook
ML_FEATURES = [
    "water_level_node1",
    "water_level_node2",
    "level_diff",
    "rise_rate_node1",
    "rise_rate_node2",
    "rain_hour",
    "rain_intensity",
]

db_lock = Lock()

# How old a sensor/weather row can be before it's treated as stale
STALE_THRESHOLD_SECONDS = 30

# ─────────────────────────────────────────────
# LOAD ML MODEL
# ─────────────────────────────────────────────

model = None
label_encoder = None

try:
    model = joblib.load("model.joblib")
    log.info("✓ ML model loaded")
except Exception as e:
    log.warning(f"ML model not loaded: {e}")

try:
    label_encoder = joblib.load("encoder.joblib")
    log.info("✓ Label encoder loaded")
except Exception as e:
    log.warning(f"Label encoder not loaded: {e}  — using fallback index mapping")

# Fallback mapping when encoder is missing (matches LabelEncoder on ['blockage','flood','normal'])
_LABEL_MAP = {0: "blockage", 1: "flood", 2: "normal"}


def decode_label(idx: int) -> str:
    if label_encoder is not None:
        return label_encoder.inverse_transform([idx])[0].upper()
    return _LABEL_MAP.get(idx, "UNKNOWN").upper()


# ─────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────


def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        log.error(f"DB connection error: {e}")
        return None


def _use_db(cursor):
    cursor.execute(f"USE `{DB_CONFIG['database']}`")


def _serialize(row):
    """Convert datetime fields to ISO strings for JSON serialisation."""
    if row is None:
        return None
    out = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def is_stale(row) -> bool:
    """
    Return True if the row is missing or its timestamp is older than
    STALE_THRESHOLD_SECONDS.  Handles both raw datetime objects (straight
    from the MySQL cursor) and ISO strings (after _serialize()).
    """
    if not row or not row.get("timestamp"):
        return True
    ts = row["timestamp"]
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    return (datetime.now() - ts).total_seconds() > STALE_THRESHOLD_SECONDS


def init_database():
    # Connect without selecting a DB first so we can CREATE it
    cfg = {**DB_CONFIG}
    cfg.pop("database", None)
    try:
        conn = mysql.connector.connect(**cfg)
    except Error as e:
        log.error(f"Cannot connect to MySQL: {e}")
        return

    cursor = conn.cursor()
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{DB_CONFIG['database']}`")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                device_id   TINYINT      NOT NULL,
                water_level FLOAT        NOT NULL,
                rise_rate   FLOAT        NOT NULL DEFAULT 0,
                percentage  FLOAT        NOT NULL DEFAULT 0,
                timestamp   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_device_ts (device_id, timestamp)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id                  INT AUTO_INCREMENT PRIMARY KEY,
                water_level1        FLOAT NOT NULL,
                water_level2        FLOAT NOT NULL,
                level_difference    FLOAT NOT NULL,
                rise_rate1          FLOAT NOT NULL,
                rise_rate2          FLOAT NOT NULL,
                rain_mm             FLOAT NOT NULL DEFAULT 0,
                rain_hour           FLOAT NOT NULL DEFAULT 0,
                condition_label     VARCHAR(20) NOT NULL DEFAULT 'NORMAL',
                flood_probability   FLOAT NOT NULL DEFAULT 0,
                blockage_probability FLOAT NOT NULL DEFAULT 0,
                ml_label            VARCHAR(20),
                timestamp           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_ts (timestamp)
            )
        """
        )

        # ── Migration: add columns that may be missing from an older schema ──
        migrations = [
            ("condition_label",      "ALTER TABLE predictions ADD COLUMN condition_label VARCHAR(20) NOT NULL DEFAULT 'NORMAL' AFTER rain_hour"),
            ("ml_label",             "ALTER TABLE predictions ADD COLUMN ml_label VARCHAR(20) AFTER blockage_probability"),
            ("flood_probability",    "ALTER TABLE predictions ADD COLUMN flood_probability FLOAT NOT NULL DEFAULT 0 AFTER condition_label"),
            ("blockage_probability", "ALTER TABLE predictions ADD COLUMN blockage_probability FLOAT NOT NULL DEFAULT 0 AFTER flood_probability"),
        ]
        cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='predictions'",
                       (DB_CONFIG['database'],))
        existing_cols = {r[0] for r in cursor.fetchall()}
        for col, ddl in migrations:
            if col not in existing_cols:
                try:
                    cursor.execute(ddl)
                    log.info(f"Migration: added column '{col}' to predictions")
                except Error as me:
                    log.warning(f"Migration skipped ({col}): {me}")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_data (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                rain_mm     FLOAT NOT NULL DEFAULT 0,
                rain_hour   FLOAT NOT NULL DEFAULT 0,
                temperature FLOAT NOT NULL DEFAULT 0,
                humidity    FLOAT NOT NULL DEFAULT 0,
                timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_ts (timestamp)
            )
        """
        )

        conn.commit()
        log.info("✓ Database initialised")
    except Error as e:
        log.error(f"DB init error: {e}")
    finally:
        cursor.close()
        conn.close()


# ─────────────────────────────────────────────
# WEATHER
# ─────────────────────────────────────────────

_DUMMY_WEATHER = {"rain_mm": 0.0, "rain_hour": 0.0, "temperature": 28.0, "humidity": 65.0}


def fetch_weather_data() -> dict:
    if not TOMORROW_API_KEY:
        log.debug("No Tomorrow.io key — using dummy weather")
        return _DUMMY_WEATHER.copy()

    try:
        resp = requests.get(
            TOMORROW_API_URL,
            params={
                "location": f"{LOCATION_LAT},{LOCATION_LON}",
                "apikey": TOMORROW_API_KEY,
                "units": "metric",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        vals = data.get("data", {}).get("values", {})
        return {
            "rain_mm": float(vals.get("precipitationIntensity", 0)),
            "rain_hour": float(vals.get("precipitationProbability", 0)),
            "temperature": float(vals.get("temperature", 0)),
            "humidity": float(vals.get("humidity", 0)),
        }
    except Exception as e:
        log.warning(f"Weather API error: {e}")
        return _DUMMY_WEATHER.copy()


def store_weather_data(weather: dict) -> bool:
    with db_lock:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            _use_db(cursor)
            cursor.execute(
                "INSERT INTO weather_data (rain_mm, rain_hour, temperature, humidity) VALUES (%s,%s,%s,%s)",
                (weather["rain_mm"], weather["rain_hour"], weather["temperature"], weather["humidity"]),
            )
            conn.commit()
            return True
        except Error as e:
            log.error(f"store_weather_data: {e}")
            return False
        finally:
            cursor.close()
            conn.close()


def get_latest_weather() -> dict:
    with db_lock:
        conn = get_db_connection()
        if not conn:
            return _DUMMY_WEATHER.copy()
        cursor = conn.cursor(dictionary=True)
        try:
            _use_db(cursor)
            cursor.execute(
                "SELECT rain_mm, rain_hour, temperature, humidity, timestamp "
                "FROM weather_data ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if not row:
                return _DUMMY_WEATHER.copy()
            # Return dummy values if the last weather fetch is stale
            if is_stale(row):
                log.debug("Weather row is stale — returning dummy weather")
                return _DUMMY_WEATHER.copy()
            return _serialize(row)
        finally:
            cursor.close()
            conn.close()


# ─────────────────────────────────────────────
# PREDICTION
# ─────────────────────────────────────────────


def compute_prediction(wl1, wl2, rise1, rise2, rain_mm=0.0, rain_hour=0.0):
    """
    Returns (condition_str, flood_prob, blockage_prob, ml_label_str | None)
    Rule-based takes priority over ML.
    """
    diff = abs(wl1 - wl2)
    condition = "NORMAL"

    # --- RULE-BASED (priority) ---
    if wl1 > 35 or wl2 > 35:
        condition = "FLOOD"
    elif wl1 > 30 and wl2 > 30:
        condition = "FLOOD"
    elif diff > 15:
        condition = "BLOCKAGE"
    elif rise1 > 2 and rise2 < 0.5:
        condition = "BLOCKAGE"

    # --- ML (secondary, only when NORMAL from rules) ---
    ml_label = None
    flood_prob = 0.0
    blockage_prob = 0.0

    if model is not None:
        try:
            import numpy as np
            # Use numpy array (no feature names) to match how the model was trained
            features = np.array([[wl1, wl2, wl1 - wl2, rise1, rise2, rain_hour, rain_mm]])
            idx = int(model.predict(features)[0])
            proba = model.predict_proba(features)[0].tolist()
            ml_label = decode_label(idx)

            # Map probabilities: encoder sorts alphabetically → blockage=0, flood=1, normal=2
            if len(proba) == 3:
                blockage_prob = float(proba[0])
                flood_prob = float(proba[1])

            if condition == "NORMAL":
                condition = ml_label
        except Exception as e:
            log.warning(f"ML prediction error: {e}")

    return condition, flood_prob, blockage_prob, ml_label


def store_prediction(wl1, wl2, rise1, rise2, rain_mm, rain_hour, condition, flood_prob, blockage_prob, ml_label):
    with db_lock:
        conn = get_db_connection()
        if not conn:
            return
        cursor = conn.cursor()
        try:
            _use_db(cursor)
            cursor.execute(
                """INSERT INTO predictions
                   (water_level1, water_level2, level_difference,
                    rise_rate1, rise_rate2, rain_mm, rain_hour,
                    condition_label, flood_probability, blockage_probability, ml_label)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (wl1, wl2, abs(wl1 - wl2), rise1, rise2,
                 rain_mm, rain_hour, condition,
                 flood_prob, blockage_prob, ml_label),
            )
            conn.commit()
        except Error as e:
            log.error(f"store_prediction: {e}")
        finally:
            cursor.close()
            conn.close()


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/water-level", methods=["POST"])
def receive_water_level():
    """Receive JSON from ESP32 and store in DB. Triggers prediction on every insert."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    device_id = data.get("device_id")
    water_level = data.get("water_level")
    rise_rate = data.get("rise_rate", 0.0)
    percentage = data.get("percentage", 0.0)

    if device_id is None or water_level is None:
        return jsonify({"error": "Missing device_id or water_level"}), 400

    with db_lock:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "DB unavailable"}), 500
        cursor = conn.cursor()
        try:
            _use_db(cursor)
            cursor.execute(
                "INSERT INTO sensor_readings (device_id, water_level, rise_rate, percentage) VALUES (%s,%s,%s,%s)",
                (device_id, float(water_level), float(rise_rate), float(percentage)),
            )
            conn.commit()
        except Error as e:
            log.error(f"receive_water_level DB error: {e}")
            return jsonify({"error": "DB write failed"}), 500
        finally:
            cursor.close()
            conn.close()

    log.info(f"Device {device_id} → level={water_level:.2f}cm rate={rise_rate:.4f}cm/s pct={percentage:.1f}%")

    # Auto-predict after each insert (non-blocking fire-and-forget style)
    _run_prediction_async()

    return jsonify({"status": "ok", "device_id": device_id}), 200


def _run_prediction_async():
    """
    Fetch both devices and compute + store a prediction.
    Called after each sensor insert.
    Skips prediction entirely if either device row is stale (device offline).
    """
    try:
        with db_lock:
            conn = get_db_connection()
            if not conn:
                return
            cursor = conn.cursor(dictionary=True)
            _use_db(cursor)
            cursor.execute(
                "SELECT water_level, rise_rate, timestamp FROM sensor_readings "
                "WHERE device_id=1 ORDER BY timestamp DESC LIMIT 1"
            )
            d1 = cursor.fetchone()
            cursor.execute(
                "SELECT water_level, rise_rate, timestamp FROM sensor_readings "
                "WHERE device_id=2 ORDER BY timestamp DESC LIMIT 1"
            )
            d2 = cursor.fetchone()
            cursor.close()
            conn.close()

        # Do not run prediction if either node is offline / stale
        if is_stale(d1) or is_stale(d2):
            log.debug("Skipping prediction — one or both sensor nodes are stale")
            return

        weather = get_latest_weather()
        cond, fp, bp, ml = compute_prediction(
            float(d1["water_level"]), float(d2["water_level"]),
            float(d1["rise_rate"]), float(d2["rise_rate"]),
            weather.get("rain_mm", 0), weather.get("rain_hour", 0),
        )
        store_prediction(
            float(d1["water_level"]), float(d2["water_level"]),
            float(d1["rise_rate"]), float(d2["rise_rate"]),
            weather.get("rain_mm", 0), weather.get("rain_hour", 0),
            cond, fp, bp, ml,
        )
    except Exception as e:
        log.warning(f"_run_prediction_async: {e}")


@app.route("/api/latest", methods=["GET"])
def get_latest_data():
    with db_lock:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "DB unavailable"}), 500
        cursor = conn.cursor(dictionary=True)
        try:
            _use_db(cursor)

            def latest_device(did):
                cursor.execute(
                    "SELECT device_id, water_level, rise_rate, percentage, timestamp "
                    "FROM sensor_readings WHERE device_id=%s ORDER BY timestamp DESC LIMIT 1",
                    (did,),
                )
                return _serialize(cursor.fetchone())

            d1 = latest_device(1)
            d2 = latest_device(2)

            # Nullify stale device data so the dashboard shows '—' instead of
            # re-displaying the last known value when a node goes offline
            if is_stale(d1):
                d1 = None
            if is_stale(d2):
                d2 = None

            cursor.execute(
                "SELECT rain_mm, rain_hour, temperature, humidity, timestamp "
                "FROM weather_data ORDER BY timestamp DESC LIMIT 1"
            )
            weather = _serialize(cursor.fetchone())

            cursor.execute(
                "SELECT condition_label, flood_probability, blockage_probability, ml_label, timestamp "
                "FROM predictions ORDER BY timestamp DESC LIMIT 1"
            )
            pred = _serialize(cursor.fetchone())

            # If the latest prediction is stale (no live data), clear it too
            if is_stale(pred):
                pred = None

            level_diff = 0.0
            if d1 and d2:
                level_diff = round(abs(d1["water_level"] - d2["water_level"]), 2)

            return jsonify({
                "status": "ok",
                "device1": d1,
                "device2": d2,
                "level_difference": level_diff,
                "weather": weather,
                "prediction": pred,
            }), 200
        except Error as e:
            log.error(f"get_latest_data: {e}")
            return jsonify({"error": "DB error"}), 500
        finally:
            cursor.close()
            conn.close()


@app.route("/api/history", methods=["GET"])
def get_history():
    device_id = request.args.get("device_id", type=int)
    hours = request.args.get("hours", default=24, type=int)
    hours = max(1, min(hours, 168))  # clamp 1–168 hours

    with db_lock:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "DB unavailable"}), 500
        cursor = conn.cursor(dictionary=True)
        try:
            _use_db(cursor)
            if device_id:
                cursor.execute(
                    "SELECT device_id, water_level, rise_rate, percentage, timestamp "
                    "FROM sensor_readings "
                    "WHERE device_id=%s AND timestamp >= DATE_SUB(NOW(), INTERVAL %s HOUR) "
                    "ORDER BY timestamp ASC",
                    (device_id, hours),
                )
            else:
                cursor.execute(
                    "SELECT device_id, water_level, rise_rate, percentage, timestamp "
                    "FROM sensor_readings "
                    "WHERE timestamp >= DATE_SUB(NOW(), INTERVAL %s HOUR) "
                    "ORDER BY timestamp ASC",
                    (hours,),
                )
            rows = [_serialize(r) for r in cursor.fetchall()]
            return jsonify({"status": "ok", "count": len(rows), "data": rows}), 200
        except Error as e:
            log.error(f"get_history: {e}")
            return jsonify({"error": "DB error"}), 500
        finally:
            cursor.close()
            conn.close()


@app.route("/api/predict", methods=["GET"])
def predict_endpoint():
    """On-demand prediction using latest DB data + live weather."""
    with db_lock:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "DB unavailable"}), 500
        cursor = conn.cursor(dictionary=True)
        try:
            _use_db(cursor)
            cursor.execute(
                "SELECT water_level, rise_rate, timestamp FROM sensor_readings "
                "WHERE device_id=1 ORDER BY timestamp DESC LIMIT 1"
            )
            d1 = cursor.fetchone()
            cursor.execute(
                "SELECT water_level, rise_rate, timestamp FROM sensor_readings "
                "WHERE device_id=2 ORDER BY timestamp DESC LIMIT 1"
            )
            d2 = cursor.fetchone()
        except Error as e:
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    # Refuse to predict if nodes are offline
    if is_stale(d1) or is_stale(d2):
        return jsonify({
            "status": "offline",
            "message": "One or both sensor nodes are offline or stale. Cannot predict.",
        }), 200

    weather = fetch_weather_data()
    store_weather_data(weather)

    wl1, wl2 = float(d1["water_level"]), float(d2["water_level"])
    r1, r2 = float(d1["rise_rate"]), float(d2["rise_rate"])

    cond, fp, bp, ml = compute_prediction(wl1, wl2, r1, r2, weather["rain_mm"], weather["rain_hour"])
    store_prediction(wl1, wl2, r1, r2, weather["rain_mm"], weather["rain_hour"], cond, fp, bp, ml)

    return jsonify({
        "status": "ok",
        "condition": cond,
        "wl1": wl1, "wl2": wl2,
        "rise_rate1": r1, "rise_rate2": r2,
        "difference": round(abs(wl1 - wl2), 2),
        "flood_probability": round(fp, 3),
        "blockage_probability": round(bp, 3),
        "ml_label": ml,
        "weather": weather,
    }), 200


@app.route("/api/device/<int:device_id>/stats", methods=["GET"])
def device_stats(device_id):
    with db_lock:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "DB unavailable"}), 500
        cursor = conn.cursor(dictionary=True)
        try:
            _use_db(cursor)
            cursor.execute(
                """SELECT
                    COUNT(*)          AS total_readings,
                    ROUND(AVG(water_level), 2) AS avg_level,
                    ROUND(MIN(water_level), 2) AS min_level,
                    ROUND(MAX(water_level), 2) AS max_level,
                    ROUND(AVG(rise_rate), 4)   AS avg_rise_rate,
                    ROUND(MAX(rise_rate), 4)   AS max_rise_rate,
                    ROUND(MIN(rise_rate), 4)   AS min_rise_rate,
                    MIN(timestamp)             AS first_reading,
                    MAX(timestamp)             AS last_reading
                FROM sensor_readings WHERE device_id=%s""",
                (device_id,),
            )
            stats = _serialize(cursor.fetchone())
            return jsonify({"status": "ok", "device_id": device_id, "stats": stats}), 200
        except Error as e:
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()


@app.route("/api/weather", methods=["GET"])
def weather_endpoint():
    w = fetch_weather_data()
    store_weather_data(w)
    return jsonify({"status": "ok", "data": w}), 200


@app.route("/api/reset", methods=["POST"])
def reset_data():
    with db_lock:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "DB unavailable"}), 500
        cursor = conn.cursor()
        try:
            _use_db(cursor)
            for tbl in ("sensor_readings", "predictions", "weather_data"):
                cursor.execute(f"DELETE FROM {tbl}")
            conn.commit()
            log.warning("All data reset by user request")
            return jsonify({"status": "ok", "message": "All data cleared"}), 200
        except Error as e:
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  IoT Flood Monitoring System — Flask Server")
    print("=" * 55)
    init_database()
    print(f"  DB   : {DB_CONFIG['database']}@{DB_CONFIG['host']}")
    print(f"  ML   : {'✓ loaded' if model else '✗ not loaded (rule-based only)'}")
    print(f"  URL  : http://0.0.0.0:5000")
    print("=" * 55)
    app.run(debug=False, host="0.0.0.0", port=5000)