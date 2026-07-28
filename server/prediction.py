import logging
from pathlib import Path

import joblib
import numpy as np
from mysql.connector import Error

from config import MODEL_FALLBACK_FILES, MODEL_FILES, _FALLBACK_LABEL_MAP
from db import db_lock, get_db_connection, _use_db

log = logging.getLogger(__name__)

model = None
label_encoder = None


def _resolve_model_path(name: str) -> Path:
    for candidate in (MODEL_FILES[name], MODEL_FALLBACK_FILES[name], Path(name)):
        if candidate.exists():
            return candidate
    return MODEL_FILES[name]


def load_models():
    global model, label_encoder

    try:
        model_path = _resolve_model_path("model")
        model = joblib.load(model_path)
        log.info(f"✓ ML model loaded from {model_path}")
    except Exception as exc:
        log.warning(f"ML model not loaded: {exc}")

    try:
        encoder_path = _resolve_model_path("encoder")
        label_encoder = joblib.load(encoder_path)
        log.info(f"✓ Label encoder loaded from {encoder_path}")
    except Exception as exc:
        log.warning(f"Label encoder not loaded: {exc} — using fallback index mapping")


def decode_label(index: int) -> str:
    if label_encoder is not None:
        return label_encoder.inverse_transform([index])[0].upper()
    return _FALLBACK_LABEL_MAP.get(index, "UNKNOWN").upper()


load_models()


def compute_prediction(wl1, wl2, rise1, rise2, rain_mm=0.0, rain_hour=0.0):
    """
    Returns (condition_str, flood_prob, blockage_prob, ml_label_str | None).
    Rule-based takes priority over ML.
    """
    diff = abs(wl1 - wl2)
    condition = "NORMAL"

    if wl1 > 35 or wl2 > 35:
        condition = "FLOOD"
    elif wl1 > 30 and wl2 > 30:
        condition = "FLOOD"
    elif diff > 15:
        condition = "BLOCKAGE"
    elif rise1 > 2 and rise2 < 0.5:
        condition = "BLOCKAGE"

    ml_label = None
    flood_prob = 0.0
    blockage_prob = 0.0

    if model is not None:
        try:
            features = np.array([[wl1, wl2, wl1 - wl2, rise1, rise2, rain_hour, rain_mm]], dtype=float)
            index = int(model.predict(features)[0])
            probabilities = model.predict_proba(features)[0].tolist()
            ml_label = decode_label(index)

            if len(probabilities) == 3:
                blockage_prob = float(probabilities[0])
                flood_prob = float(probabilities[1])

            if condition == "NORMAL":
                condition = ml_label
        except Exception as exc:
            log.warning(f"ML prediction error: {exc}")

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
                (
                    wl1,
                    wl2,
                    abs(wl1 - wl2),
                    rise1,
                    rise2,
                    rain_mm,
                    rain_hour,
                    condition,
                    flood_prob,
                    blockage_prob,
                    ml_label,
                ),
            )
            conn.commit()
        except Error as exc:
            log.error(f"store_prediction: {exc}")
        finally:
            cursor.close()
            conn.close()
