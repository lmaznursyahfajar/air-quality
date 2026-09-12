"""
metrics.py
===========
Menyimpan & membaca metrik evaluasi model (MAE, RMSE) hasil training
sungguhan, supaya tab "Time Series" bisa menampilkan perbandingan model
yang jujur -- bukan angka contoh yang di-hardcode.
"""
from __future__ import annotations

import json
from typing import Optional

from app.config import MODELS_DIR


def _path(city: str) -> "Path":
    safe = city.lower().replace(" ", "_")
    return MODELS_DIR / f"{safe}_metrics.json"


def save_metrics(city: str, model_name: str, mae: float, rmse: float, training_days: int) -> None:
    path = _path(city)
    data = {}
    if path.exists():
        with open(path, "r") as f:
            data = json.load(f)
    data[model_name] = {
        "mae": round(float(mae), 3),
        "rmse": round(float(rmse), 3),
        "training_days": training_days,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_metrics(city: str) -> Optional[dict]:
    path = _path(city)
    if not path.exists():
        return None
    with open(path, "r") as f:
        return json.load(f)
