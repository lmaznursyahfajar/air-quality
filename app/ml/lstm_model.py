"""
lstm_model.py
==============
Model LSTM (Long Short-Term Memory) sungguhan untuk prediksi PM2.5 harian,
dilatih dari data yang tersimpan di database (bukan simulasi). Data per-jam
dari OpenWeatherMap diagregasi menjadi rata-rata harian sebelum dilatih,
karena target prediksi aplikasi ini adalah tren harian (7-90 hari ke depan).

File model tersimpan di models/<kota>_lstm.h5 dan scaler di
models/<kota>_lstm_scaler.pkl, dimuat ulang oleh aplikasi Streamlit tanpa
perlu melatih ulang setiap kali dibuka.

Minimal data yang disarankan: >= 60 hari data harian agar hasil bermakna
secara statistik (LSTM butuh cukup banyak contoh sequence untuk belajar pola).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import joblib

from app.config import MODELS_DIR
from app.ml.metrics import save_metrics

WINDOW_SIZE = 14  # jumlah hari historis yang dilihat model untuk memprediksi 1 hari ke depan
MIN_TRAINING_DAYS = 45  # minimum hari data harian agar training dianggap layak


class InsufficientDataError(RuntimeError):
    pass


def _lazy_import_tf():
    try:
        import tensorflow as tf  # noqa: F401
        from tensorflow.keras.models import Sequential, load_model  # noqa: F401
        from tensorflow.keras.layers import LSTM, Dense, Dropout  # noqa: F401
        from sklearn.preprocessing import MinMaxScaler  # noqa: F401
        return tf, Sequential, load_model, LSTM, Dense, Dropout, MinMaxScaler
    except ImportError as exc:
        raise ImportError(
            "TensorFlow / scikit-learn belum terpasang. Jalankan: "
            "pip install tensorflow scikit-learn"
        ) from exc


def _daily_series(df_hourly: pd.DataFrame) -> pd.Series:
    s = df_hourly.set_index("timestamp")["pm2_5"].resample("D").mean().dropna()
    return s


def _make_sequences(values: np.ndarray, window: int):
    X, y = [], []
    for i in range(len(values) - window):
        X.append(values[i:i + window])
        y.append(values[i + window])
    return np.array(X), np.array(y)


def _model_paths(city: str):
    safe = city.lower().replace(" ", "_")
    return MODELS_DIR / f"{safe}_lstm.h5", MODELS_DIR / f"{safe}_lstm_scaler.pkl"


def train_and_save(city: str, df_hourly: pd.DataFrame, epochs: int = 60) -> dict:
    """Melatih LSTM untuk satu kota dari data mentah per-jam, lalu menyimpan model + scaler."""
    tf, Sequential, load_model, LSTM, Dense, Dropout, MinMaxScaler = _lazy_import_tf()

    daily = _daily_series(df_hourly)
    if len(daily) < MIN_TRAINING_DAYS:
        raise InsufficientDataError(
            f"Data harian untuk {city} baru {len(daily)} hari, minimal {MIN_TRAINING_DAYS} hari "
            "diperlukan agar LSTM bisa dilatih dengan layak. Biarkan proses ingestion berjalan "
            "lebih lama, atau jalankan scripts/seed_historical.py untuk backfill data historis."
        )

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(daily.values.reshape(-1, 1)).flatten()

    X, y = _make_sequences(scaled, WINDOW_SIZE)
    X = X.reshape((X.shape[0], X.shape[1], 1))

    split = max(1, int(len(X) * 0.85))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    model = Sequential([
        LSTM(64, activation="tanh", return_sequences=True, input_shape=(WINDOW_SIZE, 1)),
        Dropout(0.2),
        LSTM(32, activation="tanh"),
        Dropout(0.2),
        Dense(16, activation="relu"),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val) if len(X_val) > 0 else None,
        epochs=epochs,
        batch_size=8,
        verbose=0,
    )

    model_path, scaler_path = _model_paths(city)
    model.save(model_path)
    joblib.dump(scaler, scaler_path)

    # Hitung MAE/RMSE dalam satuan asli (µg/m³), bukan skala 0-1, agar bisa
    # dibandingkan langsung dengan model lain (mis. Prophet).
    if len(X_val) > 0:
        val_pred_scaled = model.predict(X_val, verbose=0).flatten()
        val_pred = scaler.inverse_transform(val_pred_scaled.reshape(-1, 1)).flatten()
        val_true = scaler.inverse_transform(y_val.reshape(-1, 1)).flatten()
        mae = float(np.mean(np.abs(val_pred - val_true)))
        rmse = float(np.sqrt(np.mean((val_pred - val_true) ** 2)))
        save_metrics(city, "LSTM", mae, rmse, len(daily))
    else:
        mae = rmse = None

    return {
        "city": city,
        "training_days": len(daily),
        "val_mae_ugm3": round(mae, 3) if mae is not None else None,
        "val_rmse_ugm3": round(rmse, 3) if rmse is not None else None,
        "model_path": str(model_path),
    }


def model_exists(city: str) -> bool:
    model_path, scaler_path = _model_paths(city)
    return model_path.exists() and scaler_path.exists()


def predict_future(city: str, df_hourly: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    """Memuat model tersimpan dan memprediksi `days` hari ke depan secara iteratif (recursive forecasting)."""
    tf, Sequential, load_model, LSTM, Dense, Dropout, MinMaxScaler = _lazy_import_tf()

    model_path, scaler_path = _model_paths(city)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Belum ada model LSTM terlatih untuk {city}. Jalankan scripts/train_models.py terlebih dahulu."
        )

    model = load_model(model_path)
    scaler = joblib.load(scaler_path)

    daily = _daily_series(df_hourly)
    if len(daily) < WINDOW_SIZE:
        raise InsufficientDataError(f"Butuh minimal {WINDOW_SIZE} hari data untuk membentuk window prediksi.")

    window = scaler.transform(daily.values[-WINDOW_SIZE:].reshape(-1, 1)).flatten()

    preds_scaled = []
    current_window = window.copy()
    for _ in range(days):
        x_in = current_window.reshape(1, WINDOW_SIZE, 1)
        next_scaled = float(model.predict(x_in, verbose=0)[0, 0])
        preds_scaled.append(next_scaled)
        current_window = np.append(current_window[1:], next_scaled)

    preds = scaler.inverse_transform(np.array(preds_scaled).reshape(-1, 1)).flatten()
    preds = np.clip(preds, 0, None)

    future_dates = pd.date_range(start=daily.index[-1] + pd.Timedelta(days=1), periods=days, freq="D")
    return pd.DataFrame({"date": future_dates, "predicted_pm25": preds, "model": "LSTM"})
