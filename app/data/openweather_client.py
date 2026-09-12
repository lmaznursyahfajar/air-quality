"""
openweather_client.py
======================
Wrapper tipis di atas OpenWeatherMap REST API:

- Air Pollution API (current & history)  -> PM2.5, PM10, NO2, SO2, O3, CO
- Current Weather API                    -> suhu, kelembaban, angin, hujan

Kedua endpoint ini GRATIS di semua tier OpenWeatherMap (termasuk free tier).
Daftar API key: https://home.openweathermap.org/users/sign_up

Modul ini TIDAK menyentuh database -- hanya bertanggung jawab mengambil
data mentah dari API dan mengubahnya ke bentuk dict/records yang siap
disimpan. Logika penyimpanan ada di app/data/ingestion.py.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import requests

from app.config import OPENWEATHER_API_KEY, OPENWEATHER_BASE_URL


class OpenWeatherError(RuntimeError):
    pass


def _require_api_key() -> None:
    if not OPENWEATHER_API_KEY:
        raise OpenWeatherError(
            "OPENWEATHER_API_KEY belum diset. Buat file .env (lihat .env.example) "
            "dan daftar API key gratis di https://home.openweathermap.org/users/sign_up"
        )


def _get(url: str, params: dict, retries: int = 3, backoff: float = 2.0) -> dict:
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 401:
                raise OpenWeatherError(
                    "API key ditolak (401). Periksa OPENWEATHER_API_KEY di .env. "
                    "Catatan: key baru butuh beberapa menit sampai aktif."
                )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(backoff * attempt)
    raise OpenWeatherError(f"Gagal memanggil OpenWeatherMap setelah {retries} percobaan: {last_err}")


def fetch_current_air_pollution(lat: float, lon: float) -> dict:
    """Polusi udara saat ini untuk satu koordinat."""
    _require_api_key()
    url = f"{OPENWEATHER_BASE_URL}/data/2.5/air_pollution"
    data = _get(url, {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY})
    item = data["list"][0]
    return {
        "timestamp": datetime.fromtimestamp(item["dt"], tz=timezone.utc).replace(tzinfo=None),
        "pm2_5": item["components"].get("pm2_5"),
        "pm10": item["components"].get("pm10"),
        "no2": item["components"].get("no2"),
        "so2": item["components"].get("so2"),
        "o3": item["components"].get("o3"),
        "co": item["components"].get("co"),
    }


def fetch_historical_air_pollution(lat: float, lon: float, start: datetime, end: datetime) -> list[dict]:
    """
    Riwayat polusi udara per jam antara `start` dan `end` (UTC, naive datetime).
    OpenWeatherMap menyediakan data historis air pollution sejak 27 Nov 2020.
    Dipakai untuk backfill dataset training model (scripts/seed_historical.py).
    """
    _require_api_key()
    url = f"{OPENWEATHER_BASE_URL}/data/2.5/air_pollution/history"
    params = {
        "lat": lat,
        "lon": lon,
        "start": int(start.replace(tzinfo=timezone.utc).timestamp()),
        "end": int(end.replace(tzinfo=timezone.utc).timestamp()),
        "appid": OPENWEATHER_API_KEY,
    }
    data = _get(url, params)
    results = []
    for item in data.get("list", []):
        results.append({
            "timestamp": datetime.fromtimestamp(item["dt"], tz=timezone.utc).replace(tzinfo=None),
            "pm2_5": item["components"].get("pm2_5"),
            "pm10": item["components"].get("pm10"),
            "no2": item["components"].get("no2"),
            "so2": item["components"].get("so2"),
            "o3": item["components"].get("o3"),
            "co": item["components"].get("co"),
        })
    return results


def fetch_current_weather(lat: float, lon: float) -> dict:
    """Cuaca saat ini (suhu, kelembaban, angin, hujan) untuk satu koordinat."""
    _require_api_key()
    url = f"{OPENWEATHER_BASE_URL}/data/2.5/weather"
    data = _get(url, {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric"})
    return {
        "temperature": data.get("main", {}).get("temp"),
        "humidity": data.get("main", {}).get("humidity"),
        "wind_speed": data.get("wind", {}).get("speed"),
        "rainfall": data.get("rain", {}).get("1h", 0.0),
    }
