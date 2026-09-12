"""
config.py
=========
Konfigurasi terpusat untuk seluruh aplikasi: kota yang dipantau, koneksi
database, API key, serta ambang batas kategori ISPU (Indeks Standar
Pencemar Udara) untuk parameter PM2.5.

Semua modul lain (ingestion, ml, views) mengimpor nilai dari sini agar
tidak ada konfigurasi yang terduplikasi / tidak konsisten.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# --------------------------------------------------------------------------
# Load variabel dari file .env (jika ada) sebelum membaca os.environ
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --------------------------------------------------------------------------
# Direktori
# --------------------------------------------------------------------------
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
# Default: SQLite lokal (cocok untuk pengembangan / server sendiri + cron).
# Untuk deployment cloud (mis. Streamlit Community Cloud) gunakan Postgres
# gratis (Supabase / Neon / Railway) dan set DATABASE_URL di secrets, karena
# filesystem Streamlit Cloud tidak persisten dan tidak bisa menjalankan cron.
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'pm25.db'}")

# --------------------------------------------------------------------------
# API Keys
# --------------------------------------------------------------------------
# Daftar gratis di https://home.openweathermap.org/users/sign_up
# Air Pollution API & Current Weather API tersedia di tier gratis.
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org"

# --------------------------------------------------------------------------
# Kota yang dipantau (nama, lat, lon, provinsi)
# --------------------------------------------------------------------------
CITIES = {
    "Jakarta": {"lat": -6.2088, "lon": 106.8456, "province": "DKI Jakarta"},
    "Bandung": {"lat": -6.9175, "lon": 107.6191, "province": "Jawa Barat"},
    "Surabaya": {"lat": -7.2575, "lon": 112.7521, "province": "Jawa Timur"},
    "Medan": {"lat": 3.5952, "lon": 98.6722, "province": "Sumatera Utara"},
    "Makassar": {"lat": -5.1477, "lon": 119.4327, "province": "Sulawesi Selatan"},
}
DEFAULT_CITY = "Jakarta"

# --------------------------------------------------------------------------
# Kategori ISPU untuk PM2.5 (24-jam), mengacu Permen LHK No. 14 Tahun 2020,
# divalidasi terhadap breakpoint resmi yang dipublikasikan BMKG
# (bmkg.go.id/kualitas-udara/pm25).
# --------------------------------------------------------------------------
ISPU_BREAKPOINTS = [
    # (batas_bawah, batas_atas, label, warna, emoji)
    (0.0, 15.5, "BAIK", "#22c55e", "🟢"),
    (15.6, 55.4, "SEDANG", "#eab308", "🟡"),
    (55.5, 150.4, "TIDAK SEHAT", "#f97316", "🟠"),
    (150.5, 250.4, "SANGAT TIDAK SEHAT", "#ef4444", "🔴"),
    (250.5, float("inf"), "BERBAHAYA", "#7f1d1d", "⚫"),
]

# --------------------------------------------------------------------------
# Pengaturan ingestion / scheduler
# --------------------------------------------------------------------------
# Interval pengambilan data otomatis (menit). Data historis Air Pollution
# API OpenWeatherMap tersedia per jam, jadi 60 menit sudah representatif.
INGEST_INTERVAL_MINUTES = int(os.getenv("INGEST_INTERVAL_MINUTES", "60"))

# Berapa hari cache data di dashboard dianggap masih segar sebelum
# Streamlit menarik ulang dari database (bukan dari internet -> ringan)
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
