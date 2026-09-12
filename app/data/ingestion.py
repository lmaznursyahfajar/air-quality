"""
ingestion.py
=============
Menggabungkan data polusi udara + cuaca dari OpenWeatherMap lalu
menyimpannya ke database. Inilah inti dari alur "real-time tanpa perlu
membuka web app dulu": fungsi-fungsi di sini dipanggil oleh proses yang
BERDIRI SENDIRI dari Streamlit (cron job / GitHub Actions / scheduler),
sehingga database selalu berisi data terbaru begitu proses tersebut
berjalan -- terlepas dari apakah ada orang yang sedang membuka dashboard.

Dipakai oleh:
    - scripts/ingest_once.py   (dijalankan oleh cron / systemd timer / GitHub Actions)
    - scripts/run_scheduler.py (proses panjang yang loop sendiri, alternatif cron)
"""
from __future__ import annotations

import logging
from datetime import datetime

from app.config import CITIES
from app.database import upsert_reading, init_db
from app.data.openweather_client import (
    fetch_current_air_pollution,
    fetch_current_weather,
    OpenWeatherError,
)

logger = logging.getLogger("ingestion")


def fetch_and_store_city(city_name: str) -> bool:
    """Ambil data terbaru untuk satu kota dan simpan ke DB. Return True jika baris baru tersimpan."""
    if city_name not in CITIES:
        raise ValueError(f"Kota '{city_name}' tidak terdaftar di app/config.py -> CITIES")

    coords = CITIES[city_name]
    lat, lon = coords["lat"], coords["lon"]

    pollution = fetch_current_air_pollution(lat, lon)
    try:
        weather = fetch_current_weather(lat, lon)
    except OpenWeatherError as exc:
        # Data polusi lebih kritikal daripada cuaca -- tetap simpan meski cuaca gagal.
        logger.warning("Gagal ambil cuaca untuk %s: %s", city_name, exc)
        weather = {"temperature": None, "humidity": None, "wind_speed": None, "rainfall": None}

    row = {
        "city": city_name,
        "timestamp": pollution["timestamp"],
        "pm2_5": pollution["pm2_5"],
        "pm10": pollution["pm10"],
        "no2": pollution["no2"],
        "so2": pollution["so2"],
        "o3": pollution["o3"],
        "co": pollution["co"],
        "temperature": weather["temperature"],
        "humidity": weather["humidity"],
        "wind_speed": weather["wind_speed"],
        "rainfall": weather["rainfall"],
        "source": "openweathermap",
        "fetched_at": datetime.utcnow(),
    }
    inserted = upsert_reading(row)
    if inserted:
        logger.info("Tersimpan: %s @ %s -> PM2.5 = %.1f µg/m³", city_name, row["timestamp"], row["pm2_5"])
    else:
        logger.info("Dilewati (duplikat jam yang sama): %s @ %s", city_name, row["timestamp"])
    return inserted


def fetch_and_store_all() -> dict:
    """Ambil data terbaru untuk seluruh kota di CITIES. Return ringkasan hasil per kota."""
    init_db()
    summary = {}
    for city_name in CITIES:
        try:
            summary[city_name] = "baru" if fetch_and_store_city(city_name) else "duplikat"
        except Exception as exc:  # noqa: BLE001 - ingestion tidak boleh berhenti karena 1 kota gagal
            logger.error("Gagal mengambil data untuk %s: %s", city_name, exc)
            summary[city_name] = f"gagal: {exc}"
    return summary
