import logging
import threading
from datetime import datetime

import requests
from mysql.connector import Error

from config import DUMMY_WEATHER, LOCATION_LAT, LOCATION_LON, TOMORROW_API_KEY, TOMORROW_API_URL
from db import db_lock, get_db_connection, is_stale, serialize_row, _use_db

log = logging.getLogger(__name__)

_FORECAST_URL = "https://api.tomorrow.io/v4/weather/forecast"
_SYNC_THREAD_STARTED = False


def _coerce_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if not value:
        return datetime.now()
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed.replace(tzinfo=None)
    except ValueError:
        return datetime.now()


def fetch_weather_data() -> dict:
    """Fetch a single weather snapshot for prediction usage."""
    if not TOMORROW_API_KEY:
        log.debug("No Tomorrow.io key — using dummy weather")
        return DUMMY_WEATHER.copy()

    try:
        response = requests.get(
            _FORECAST_URL,
            params={
                "location": f"{LOCATION_LAT},{LOCATION_LON}",
                "apikey": TOMORROW_API_KEY,
                "units": "metric",
                "timesteps": "1h",
                "startTime": "now",
                "timezone": "Asia/Kolkata",
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        hourly = data.get("timelines", {}).get("hourly", [])
        if not hourly:
            log.debug("Unexpected weather response shape, keys: %s", list(data.keys()))
            return DUMMY_WEATHER.copy()

        first = hourly[0].get("values", {}) or {}
        return {
            "rain_mm": float(first.get("precipitationIntensity", 0)),
            "rain_hour": float(first.get("precipitationProbability", 0)),
            "temperature": float(first.get("temperature", 0)),
            "humidity": float(first.get("humidity", 0)),
        }
    except Exception as exc:
        log.warning(f"Weather API error: {exc}")
        return DUMMY_WEATHER.copy()


def fetch_weather_forecast_batch() -> list[dict]:
    """Fetch the next 24 hourly forecast entries from Tomorrow.io."""
    if not TOMORROW_API_KEY:
        return []

    try:
        response = requests.get(
            _FORECAST_URL,
            params={
                "location": f"{LOCATION_LAT},{LOCATION_LON}",
                "apikey": TOMORROW_API_KEY,
                "units": "metric",
                "timesteps": "1h",
                "startTime": "now",
                "timezone": "Asia/Kolkata",
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        hourly = data.get("timelines", {}).get("hourly", [])
        forecasts = []
        for item in hourly[:24]:
            values = item.get("values", {}) or {}
            forecasts.append({
                "timestamp": _coerce_datetime(item.get("time")),
                "rain_mm": float(values.get("precipitationIntensity", 0)),
                "rain_hour": float(values.get("precipitationProbability", 0)),
                "temperature": float(values.get("temperature", 0)),
                "humidity": float(values.get("humidity", 0)),
            })
        return forecasts
    except Exception as exc:
        log.warning(f"Weather forecast fetch error: {exc}")
        return []


def store_weather_data(weather: dict) -> bool:
    with db_lock:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            _use_db(cursor)
            cursor.execute(
                "INSERT INTO weather_data (rain_mm, rain_hour, temperature, humidity, timestamp) VALUES (%s,%s,%s,%s,%s)",
                (weather["rain_mm"], weather["rain_hour"], weather["temperature"], weather["humidity"], datetime.now()),
            )
            conn.commit()
            return True
        except Error as exc:
            log.error(f"store_weather_data: {exc}")
            return False
        finally:
            cursor.close()
            conn.close()


def store_weather_forecast_batch(forecasts: list[dict]) -> bool:
    if not forecasts:
        return False

    with db_lock:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            _use_db(cursor)
            for forecast in forecasts:
                cursor.execute(
                    "INSERT INTO weather_data (rain_mm, rain_hour, temperature, humidity, timestamp) VALUES (%s,%s,%s,%s,%s)",
                    (
                        forecast.get("rain_mm", 0),
                        forecast.get("rain_hour", 0),
                        forecast.get("temperature", 0),
                        forecast.get("humidity", 0),
                        forecast.get("timestamp", datetime.now()),
                    ),
                )
            conn.commit()
            return True
        except Error as exc:
            log.error(f"store_weather_forecast_batch: {exc}")
            return False
        finally:
            cursor.close()
            conn.close()


def sync_weather_forecast_batch() -> int:
    forecasts = fetch_weather_forecast_batch()
    if not forecasts:
        return 0
    if store_weather_forecast_batch(forecasts):
        log.info("Stored %d weather forecast rows", len(forecasts))
        return len(forecasts)
    return 0


def start_weather_sync_loop(interval_seconds: int = 24 * 60 * 60) -> None:
    global _SYNC_THREAD_STARTED
    if _SYNC_THREAD_STARTED:
        return

    _SYNC_THREAD_STARTED = True

    def _loop() -> None:
        try:
            sync_weather_forecast_batch()
        except Exception as exc:
            log.warning(f"Weather sync loop error: {exc}")
        finally:
            timer = threading.Timer(interval_seconds, _loop)
            timer.daemon = True
            timer.start()

    _loop()


def get_latest_weather() -> dict:
    with db_lock:
        conn = get_db_connection()
        if not conn:
            return DUMMY_WEATHER.copy()
        cursor = conn.cursor(dictionary=True)
        try:
            _use_db(cursor)
            cursor.execute(
                "SELECT rain_mm, rain_hour, temperature, humidity, timestamp "
                "FROM weather_data ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if not row:
                return DUMMY_WEATHER.copy()
            if is_stale(row):
                log.debug("Weather row is stale — returning dummy weather")
                return DUMMY_WEATHER.copy()
            return serialize_row(row)
        finally:
            cursor.close()
            conn.close()
