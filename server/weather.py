import logging

import requests
from mysql.connector import Error

from config import DUMMY_WEATHER, LOCATION_LAT, LOCATION_LON, TOMORROW_API_KEY, TOMORROW_API_URL
from db import db_lock, get_db_connection, is_stale, serialize_row, _use_db

log = logging.getLogger(__name__)


def fetch_weather_data() -> dict:
    if not TOMORROW_API_KEY:
        log.debug("No Tomorrow.io key — using dummy weather")
        return DUMMY_WEATHER.copy()

    try:
        response = requests.get(
            TOMORROW_API_URL,
            params={
                "location": f"{LOCATION_LAT},{LOCATION_LON}",
                "apikey": TOMORROW_API_KEY,
                "units": "metric",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        data_block = data.get("data", {})
        values = data_block.get("values") or {}

        if not values:
            timelines = data_block.get("timelines")
            if timelines and isinstance(timelines, list):
                try:
                    first = timelines[0]
                    intervals = first.get("intervals")
                    if intervals and isinstance(intervals, list):
                        values = intervals[0].get("values", {}) or {}
                except Exception:
                    values = {}

        if not values and any(key in data_block for key in ("temperature", "humidity", "precipitationIntensity", "precipitationProbability")):
            values = data_block

        if not values:
            log.debug(f"Unexpected weather response shape, keys: {list(data.keys())}")

        return {
            "rain_mm": float(values.get("precipitationIntensity", 0)),
            "rain_hour": float(values.get("precipitationProbability", 0)),
            "temperature": float(values.get("temperature", 0)),
            "humidity": float(values.get("humidity", 0)),
        }
    except Exception as exc:
        log.warning(f"Weather API error: {exc}")
        return DUMMY_WEATHER.copy()


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
        except Error as exc:
            log.error(f"store_weather_data: {exc}")
            return False
        finally:
            cursor.close()
            conn.close()


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
