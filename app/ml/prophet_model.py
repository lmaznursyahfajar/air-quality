"""
prophet_model.py
=================
Model Prophet (Meta/Facebook) sungguhan untuk prediksi PM2.5 harian,
sebagai pembanding LSTM. Prophet menangani musiman & tren dengan baik dan
cukup robust terhadap data yang bolong (jam-jam yang gagal ter-ingest).

File model tersimpan sebagai JSON di models/<kota>_prophet.json (format
serialisasi resmi Prophet, lebih stabil lintas versi dibanding pickle).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.config import MODELS_DIR
from app.ml.lstm_model import _daily_series, MIN_TRAINING_DAYS, InsufficientDataError
from app.ml.metrics import save_metrics


def _lazy_import_prophet():
    try:
        from prophet import Prophet
        from prophet.serialize import model_to_json, model_from_json
        return Prophet, model_to_json, model_from_json
    except ImportError as exc:
        raise ImportError("Prophet belum terpasang. Jalankan: pip install prophet") from exc


def _model_path(city: str):
    safe = city.lower().replace(" ", "_")
    return MODELS_DIR / f"{safe}_prophet.json"


def train_and_save(city: str, df_hourly: pd.DataFrame) -> dict:
    Prophet, model_to_json, _ = _lazy_import_prophet()

    daily = _daily_series(df_hourly)
    if len(daily) < MIN_TRAINING_DAYS:
        raise InsufficientDataError(
            f"Data harian untuk {city} baru {len(daily)} hari, minimal {MIN_TRAINING_DAYS} hari diperlukan."
        )

    df = daily.reset_index()
    df.columns = ["ds", "y"]

    # --- Backtest sederhana: latih di 85% data pertama, evaluasi di sisanya ---
    split = max(1, int(len(df) * 0.85))
    holdout = df.iloc[split:]
    if len(holdout) >= 3:
        backtest_model = Prophet(
            yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False,
            changepoint_prior_scale=0.1,
        )
        backtest_model.fit(df.iloc[:split])
        future = backtest_model.make_future_dataframe(periods=len(holdout))
        forecast = backtest_model.predict(future)
        pred_holdout = forecast.tail(len(holdout))["yhat"].values
        true_holdout = holdout["y"].values
        mae = float(np.mean(np.abs(pred_holdout - true_holdout)))
        rmse = float(np.sqrt(np.mean((pred_holdout - true_holdout) ** 2)))
        save_metrics(city, "Prophet", mae, rmse, len(daily))

    # --- Model final: dilatih ulang dengan SELURUH data agar prediksi ke depan optimal ---
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.1,
    )
    model.fit(df)

    path = _model_path(city)
    with open(path, "w") as f:
        f.write(model_to_json(model))

    return {"city": city, "training_days": len(daily), "model_path": str(path)}


def model_exists(city: str) -> bool:
    return _model_path(city).exists()


def predict_future(city: str, days: int = 30) -> pd.DataFrame:
    _, _, model_from_json = _lazy_import_prophet()

    path = _model_path(city)
    if not path.exists():
        raise FileNotFoundError(
            f"Belum ada model Prophet terlatih untuk {city}. Jalankan scripts/train_models.py terlebih dahulu."
        )
    with open(path, "r") as f:
        model = model_from_json(f.read())

    future = model.make_future_dataframe(periods=days)
    forecast = model.predict(future)
    tail = forecast.tail(days)[["ds", "yhat"]].rename(columns={"ds": "date", "yhat": "predicted_pm25"})
    tail["predicted_pm25"] = tail["predicted_pm25"].clip(lower=0)
    tail["model"] = "Prophet"
    return tail.reset_index(drop=True)
