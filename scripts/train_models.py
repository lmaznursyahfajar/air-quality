#!/usr/bin/env python3
"""
scripts/train_models.py
=========================
Melatih model LSTM dan Prophet untuk setiap kota menggunakan data yang
sudah tersimpan di database (hasil ingestion real-time + backfill historis).
Model hasil training disimpan di folder models/ dan dimuat ulang oleh
aplikasi Streamlit (tidak dilatih ulang setiap dashboard dibuka).

Jalankan ulang script ini secara berkala (mis. mingguan) supaya model tetap
"segar" mengikuti data terbaru -- bisa juga dijadwalkan lewat cron terpisah
dari ingest_once.py.

Pemakaian:
    python scripts/train_models.py
    python scripts/train_models.py --city Jakarta --skip-prophet
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import CITIES
from app.database import get_readings
from app.ml import lstm_model, prophet_model
from app.ml.lstm_model import InsufficientDataError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def train_city(city: str, skip_lstm: bool, skip_prophet: bool):
    df = get_readings(city)
    if df.empty:
        logging.warning("Tidak ada data sama sekali untuk %s -- lewati. Jalankan ingestion/seed dulu.", city)
        return

    if not skip_lstm:
        try:
            result = lstm_model.train_and_save(city, df)
            logging.info("LSTM %s selesai dilatih: %s", city, result)
        except InsufficientDataError as exc:
            logging.warning("LSTM %s dilewati: %s", city, exc)
        except ImportError as exc:
            logging.error(str(exc))

    if not skip_prophet:
        try:
            result = prophet_model.train_and_save(city, df)
            logging.info("Prophet %s selesai dilatih: %s", city, result)
        except InsufficientDataError as exc:
            logging.warning("Prophet %s dilewati: %s", city, exc)
        except ImportError as exc:
            logging.error(str(exc))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Latih model LSTM & Prophet dari data database")
    parser.add_argument("--city", type=str, default=None, help="Latih hanya satu kota (default: semua)")
    parser.add_argument("--skip-lstm", action="store_true")
    parser.add_argument("--skip-prophet", action="store_true")
    args = parser.parse_args()

    cities = [args.city] if args.city else list(CITIES.keys())
    for c in cities:
        if c not in CITIES:
            logging.error("Kota '%s' tidak dikenal.", c)
            continue
        logging.info("=== Melatih model untuk %s ===", c)
        train_city(c, args.skip_lstm, args.skip_prophet)

    logging.info("Selesai training semua kota.")
