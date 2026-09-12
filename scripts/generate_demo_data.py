#!/usr/bin/env python3
"""
scripts/generate_demo_data.py
===============================
OPSIONAL. Mengisi database dengan data SINTETIS (bukan data nyata) supaya
Anda bisa langsung melihat tampilan dashboard sebelum mengatur API key
sungguhan. Baris yang dihasilkan diberi tanda source="demo_synthetic" agar
mudah dibedakan dari data asli hasil ingestion OpenWeatherMap.

Untuk data SUNGGUHAN, gunakan scripts/seed_historical.py + scripts/ingest_once.py
(butuh OPENWEATHER_API_KEY). Sebaiknya hapus data demo ini sebelum
menggunakan aplikasi untuk kebutuhan nyata:

    python scripts/generate_demo_data.py --clear-first --days 75

Pemakaian:
    python scripts/generate_demo_data.py
    python scripts/generate_demo_data.py --days 30 --city Jakarta
"""
import argparse
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import CITIES
from app.database import init_db, bulk_upsert_readings, get_session, AirQualityReading

BASE_LEVEL = {"Jakarta": 45, "Bandung": 35, "Surabaya": 50, "Medan": 40, "Makassar": 30}


def generate_city(city: str, days: int, seed: int = 42):
    rng = random.Random(f"{city}-{seed}")
    base = BASE_LEVEL.get(city, 35)
    now = datetime.utcnow()
    start = now - timedelta(days=days)

    rows = []
    t = start
    i = 0
    while t <= now:
        seasonal = 10 * math.sin(2 * math.pi * i / (24 * 30))
        weekly = 4 * math.sin(2 * math.pi * i / (24 * 7))
        noise = rng.gauss(0, 8)
        pm25 = max(3.0, base + seasonal + weekly + noise)

        rows.append({
            "city": city,
            "timestamp": t,
            "pm2_5": round(pm25, 2),
            "pm10": round(pm25 * rng.uniform(1.2, 1.6), 2),
            "no2": round(rng.uniform(5, 20), 2),
            "so2": round(rng.uniform(1, 10), 2),
            "o3": round(rng.uniform(10, 40), 2),
            "co": round(rng.uniform(200, 900), 2),
            "temperature": round(26 + 5 * rng.random(), 1),
            "humidity": round(55 + 25 * rng.random(), 1),
            "wind_speed": round(1 + 4 * rng.random(), 2),
            "rainfall": round(max(0, rng.gauss(0.5, 1)), 2),
            "source": "demo_synthetic",
            "fetched_at": now,
        })
        t += timedelta(hours=1)
        i += 1
    return rows


def clear_demo_data():
    session = get_session()
    try:
        deleted = session.query(AirQualityReading).filter(
            AirQualityReading.source == "demo_synthetic"
        ).delete()
        session.commit()
        print(f"🗑️  {deleted} baris data demo lama dihapus.")
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate data demo (sintetis) untuk preview UI")
    parser.add_argument("--days", type=int, default=75, help="Jumlah hari data demo (default: 75)")
    parser.add_argument("--city", type=str, default=None, help="Hanya satu kota (default: semua)")
    parser.add_argument("--clear-first", action="store_true", help="Hapus data demo lama sebelum generate ulang")
    args = parser.parse_args()

    init_db()
    if args.clear_first:
        clear_demo_data()

    cities = [args.city] if args.city else list(CITIES.keys())
    for c in cities:
        if c not in CITIES:
            print(f"⚠️  Kota '{c}' tidak dikenal.")
            continue
        rows = generate_city(c, args.days)
        inserted = bulk_upsert_readings(rows)
        print(f"✅ {c}: {inserted} baris data demo disimpan.")

    print(
        "\n⚠️  INI DATA SINTETIS UNTUK PREVIEW UI SAJA, BUKAN DATA NYATA.\n"
        "Jalankan `streamlit run app/main.py` untuk melihat hasilnya.\n"
        "Untuk data sungguhan, ikuti panduan di README.md bagian 'Menghubungkan Data Nyata'."
    )
