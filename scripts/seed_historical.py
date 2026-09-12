#!/usr/bin/env python3
"""
scripts/seed_historical.py
============================
Mengisi database dengan data historis (bukan simulasi) dari OpenWeatherMap
Air Pollution History API, agar model LSTM/Prophet punya cukup data untuk
dilatih tanpa harus menunggu berbulan-bulan ingestion berjalan.

OpenWeatherMap menyimpan data historis air pollution sejak 27 November 2020,
jadi kita bisa mundur cukup jauh. Data cuaca historis (suhu/kelembaban/dst)
TIDAK ditarik di sini karena History Weather API berbayar -- kolom cuaca
akan kosong untuk baris hasil backfill (tidak masalah untuk training PM2.5,
karena target model adalah pm2_5; kolom cuaca hanya dipakai untuk analisis
korelasi dan otomatis terisi begitu ingestion real-time berjalan).

Pemakaian:
    python scripts/seed_historical.py --days 90
    python scripts/seed_historical.py --days 90 --city Jakarta
"""
import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import CITIES
from app.database import init_db, bulk_upsert_readings
from app.data.openweather_client import fetch_historical_air_pollution

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def seed_city(city_name: str, days: int) -> int:
    coords = CITIES[city_name]
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    logging.info("Menarik %s hari data historis untuk %s ...", days, city_name)
    records = fetch_historical_air_pollution(coords["lat"], coords["lon"], start, end)

    rows = []
    for r in records:
        rows.append({
            "city": city_name,
            "timestamp": r["timestamp"],
            "pm2_5": r["pm2_5"],
            "pm10": r["pm10"],
            "no2": r["no2"],
            "so2": r["so2"],
            "o3": r["o3"],
            "co": r["co"],
            "temperature": None,
            "humidity": None,
            "wind_speed": None,
            "rainfall": None,
            "source": "openweathermap_history",
            "fetched_at": datetime.utcnow(),
        })
    inserted = bulk_upsert_readings(rows)
    logging.info("%s: %d baris ditemukan, %d baris baru disimpan.", city_name, len(rows), inserted)
    return inserted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill data historis PM2.5 dari OpenWeatherMap")
    parser.add_argument("--days", type=int, default=90, help="Jumlah hari ke belakang (default: 90)")
    parser.add_argument("--city", type=str, default=None, help="Nama kota tunggal (default: semua kota)")
    args = parser.parse_args()

    init_db()
    cities = [args.city] if args.city else list(CITIES.keys())
    for c in cities:
        if c not in CITIES:
            logging.error("Kota '%s' tidak dikenal. Pilihan: %s", c, list(CITIES.keys()))
            continue
        seed_city(c, args.days)

    logging.info("Selesai. Jalankan scripts/train_models.py untuk melatih model prediksi.")
