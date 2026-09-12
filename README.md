# 🌫️ Prediksi Kualitas Udara PM2.5

Dashboard prediksi kualitas udara PM2.5 untuk kota-kota besar di Indonesia
(Jakarta, Bandung, Surabaya, Medan, Makassar), dibangun dengan **Streamlit**,
data **nyata** dari OpenWeatherMap, dan model **LSTM** + **Prophet** yang
benar-benar dilatih dari data historis — bukan simulasi.

Fitur utama:
- 📊 Dashboard tren, distribusi, dan status ISPU real-time
- 🔮 Prediksi 7–90 hari ke depan (LSTM & Prophet, dengan metrik MAE/RMSE nyata)
- 🌤️ Analisis korelasi PM2.5 dengan suhu, kelembaban, angin, curah hujan
- 📈 Dekomposisi time series (trend / musiman / residual) sungguhan
- 🔄 **Ingestion data otomatis** — database terisi sendiri tanpa perlu membuka web app

---

## 1. Arsitektur & Alur Data

```
OpenWeatherMap API (Air Pollution + Weather)
        │
        │  dijalankan oleh cron / systemd / GitHub Actions
        │  (BUKAN oleh Streamlit — independen sepenuhnya)
        ▼
scripts/ingest_once.py  ──────────────►  Database (SQLite / Postgres)
                                                  │
                                                  │  dibaca saja, ter-cache 5 menit
                                                  ▼
                                    streamlit run app/main.py
```

Inti dari "real-time tanpa harus membuka web dulu": proses pengambilan data
(`scripts/ingest_once.py`) adalah **skrip Python berdiri sendiri**, dijadwalkan
oleh OS (cron) atau oleh GitHub Actions. Web app **tidak pernah** memanggil API
eksternal — ia hanya membaca dari database. Jadi database akan terus terisi
setiap jam meskipun tidak ada satu pun orang yang membuka dashboard-nya.

---

## 2. Instalasi

```bash
cd pm25-dashboard
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> Instalasi TensorFlow & Prophet bisa memakan waktu beberapa menit — ini normal.

Salin file environment lalu isi API key:

```bash
cp .env.example .env
```

Buka `.env`, isi `OPENWEATHER_API_KEY` dengan key gratis dari
https://home.openweathermap.org/users/sign_up (aktivasi butuh 5–10 menit
setelah daftar).

---

## 3. Quick Start — Preview UI Instan (Data Demo)

Ingin lihat tampilannya dulu sebelum mengurus API key? Gunakan data sintetis:

```bash
python scripts/init_db.py
python scripts/generate_demo_data.py --days 75
streamlit run app/main.py
```

Data ini ditandai `source = "demo_synthetic"` di database dan **bukan data
asli** — hanya untuk melihat tampilan dashboard. Hapus sebelum pakai serius:

```bash
python scripts/generate_demo_data.py --clear-first --days 0
```

---

## 4. Menghubungkan Data Nyata

```bash
# 1. Siapkan tabel database
python scripts/init_db.py

# 2. Isi data historis (mundur hingga 90 hari) agar model bisa langsung dilatih
python scripts/seed_historical.py --days 90

# 3. Ambil data terkini satu kali (opsional, untuk cek koneksi API)
python scripts/ingest_once.py

# 4. Latih model LSTM & Prophet dari data yang sudah terkumpul
python scripts/train_models.py

# 5. Jalankan dashboard
streamlit run app/main.py
```

Catatan: `seed_historical.py` hanya mengisi kolom polutan (PM2.5, PM10, dll),
kolom cuaca (suhu/kelembaban/angin/hujan) baru terisi begitu ingestion
real-time (langkah 6 di bawah) mulai berjalan — karena History Weather API
OpenWeatherMap berbayar, sedangkan History Air Pollution API gratis.

---

## 5. Menjadwalkan Ingestion Otomatis (Real-Time)

Pilih **salah satu** sesuai tempat aplikasi dijalankan:

### A. Server / komputer sendiri (Linux/macOS) — cron
```bash
crontab -e
```
Tambahkan baris (jalan setiap jam):
```
0 * * * * cd /path/ke/pm25-dashboard && /path/ke/.venv/bin/python scripts/ingest_once.py >> logs/ingest.log 2>&1
```

### B. Server / komputer sendiri — systemd timer (lebih robust dari cron)
Buat `/etc/systemd/system/pm25-ingest.service`:
```ini
[Unit]
Description=PM2.5 Data Ingestion

[Service]
Type=oneshot
WorkingDirectory=/path/ke/pm25-dashboard
ExecStart=/path/ke/.venv/bin/python scripts/ingest_once.py
```
Buat `/etc/systemd/system/pm25-ingest.timer`:
```ini
[Unit]
Description=Jalankan PM2.5 ingestion tiap jam

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```
Aktifkan:
```bash
sudo systemctl enable --now pm25-ingest.timer
```

### C. Windows — Task Scheduler
Buat scheduled task baru yang menjalankan:
```
Program: C:\path\ke\.venv\Scripts\python.exe
Argumen: scripts\ingest_once.py
Start in: C:\path\ke\pm25-dashboard
Trigger: Daily, repeat every 1 hour
```

### D. Tanpa cron sama sekali — scheduler mandiri
Cocok untuk development atau server tanpa akses cron/systemd:
```bash
python scripts/run_scheduler.py &
```
Proses ini berjalan terus-menerus dan menarik data sendiri setiap
`INGEST_INTERVAL_MINUTES` menit (default 60, diatur di `.env`).

### E. Deploy ke cloud (Streamlit Community Cloud) — GitHub Actions
Streamlit Community Cloud **tidak punya filesystem persisten dan tidak bisa
menjalankan cron**, jadi ingestion harus dijalankan dari luar:

1. Buat database Postgres gratis (pilih salah satu: Supabase, Neon, Railway).
2. Di repo GitHub → **Settings → Secrets and variables → Actions**, tambahkan:
   - `DATABASE_URL` → connection string Postgres
   - `OPENWEATHER_API_KEY` → API key OpenWeatherMap
3. Workflow `.github/workflows/ingest.yml` sudah disiapkan — otomatis jalan
   tiap jam via GitHub Actions dan mengisi database Postgres tersebut.
4. Di **Streamlit Cloud → App settings → Secrets**, isi `DATABASE_URL` yang
   **sama persis** supaya dashboard membaca dari database yang sama.

Dengan cara ini, data tetap masuk otomatis setiap jam murni dari GitHub
Actions — sama sekali tidak bergantung pada ada/tidaknya orang membuka
dashboard.

---

## 6. Melatih Ulang Model

Jalankan berkala (mis. mingguan) supaya model mengikuti data terbaru:
```bash
python scripts/train_models.py
python scripts/train_models.py --city Jakarta          # satu kota saja
python scripts/train_models.py --skip-prophet           # hanya LSTM
```
Metrik evaluasi (MAE, RMSE dalam µg/m³) dihitung dari data validasi/holdout
ASLI setiap kali training, disimpan di `models/<kota>_metrics.json`, dan
ditampilkan di tab **Time Series** dashboard.

---

## 7. Struktur Folder

```
pm25-dashboard/
├── app/
│   ├── config.py              # kota, DB URL, API key, breakpoint ISPU
│   ├── database.py             # skema SQLAlchemy + fungsi CRUD
│   ├── styles.py                # CSS & tema Plotly
│   ├── main.py                  # entry point Streamlit
│   ├── data/
│   │   ├── openweather_client.py   # wrapper API OpenWeatherMap
│   │   └── ingestion.py             # gabung data + simpan ke DB
│   ├── ml/
│   │   ├── lstm_model.py       # training & prediksi LSTM
│   │   ├── prophet_model.py    # training & prediksi Prophet
│   │   └── metrics.py           # simpan/baca metrik evaluasi
│   ├── views/                    # satu file per tab dashboard
│   └── utils/aqi.py              # klasifikasi ISPU
├── scripts/
│   ├── init_db.py
│   ├── ingest_once.py           # dipanggil cron/GitHub Actions
│   ├── run_scheduler.py         # alternatif cron (proses panjang)
│   ├── seed_historical.py       # backfill data historis
│   ├── train_models.py
│   └── generate_demo_data.py    # data sintetis untuk preview UI
├── .github/workflows/ingest.yml # cron via GitHub Actions (opsi cloud)
├── requirements.txt
├── requirements-ingest.txt      # dependency ringan khusus GitHub Actions
└── .env.example
```

---

## 8. Sumber Data & Referensi

- **Polutan & cuaca**: [OpenWeatherMap Air Pollution API](https://openweathermap.org/api/air-pollution) & [Current Weather API](https://openweathermap.org/current) (gratis)
- **Kategori ISPU PM2.5**: Permen LHK No. 14 Tahun 2020, breakpoint divalidasi terhadap publikasi resmi [BMKG](https://www.bmkg.go.id/kualitas-udara/pm25)
- **Model**: LSTM (TensorFlow/Keras) & Prophet (Meta), dilatih dari data yang tersimpan di database, bukan angka contoh

---

## 9. Troubleshooting Singkat

| Masalah | Solusi |
|---|---|
| "OPENWEATHER_API_KEY belum diset" | Isi `.env`, key baru butuh ±10 menit untuk aktif |
| Tab Prediksi bilang "belum ada model" | Jalankan `python scripts/train_models.py` setelah data cukup (≥45 hari) |
| Data cuaca kosong di tab Analisis Cuaca | Normal untuk data hasil `seed_historical.py`; akan terisi begitu ingestion real-time berjalan |
| Dashboard kosong / "Belum ada data" | Jalankan `init_db.py` → `seed_historical.py` atau `generate_demo_data.py` |
| Deploy ke Streamlit Cloud tapi data tidak update | Pastikan pakai Postgres + GitHub Actions (lihat bagian 5E), bukan SQLite lokal |
