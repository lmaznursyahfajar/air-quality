#!/usr/bin/env python3
"""
scripts/run_scheduler.py
==========================
Alternatif untuk cron: proses PYTHON YANG BERJALAN TERUS-MENERUS
(long-running process) dan menarik data setiap INGEST_INTERVAL_MINUTES
menit sendiri, tanpa campur tangan OS scheduler. Cocok untuk:

    - Development lokal, cukup jalankan di terminal terpisah / tmux / screen
    - Server / VPS yang dikelola dengan systemd atau supervisor / pm2

Jalankan sebagai proses latar belakang, TERPISAH dari `streamlit run`:

    python scripts/run_scheduler.py &

atau daftarkan sebagai systemd service (lihat README.md).

Untuk deployment cloud tanpa proses persisten (mis. Streamlit Community
Cloud), gunakan GitHub Actions terjadwal (.github/workflows/ingest.yml)
alih-alih script ini -- lihat README.md bagian deployment cloud.
"""
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import schedule

from app.data.ingestion import fetch_and_store_all
from app.config import INGEST_INTERVAL_MINUTES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def job():
    logging.info("=== [scheduler] Menjalankan siklus ingestion ===")
    try:
        summary = fetch_and_store_all()
        for city, status in summary.items():
            logging.info("%-12s -> %s", city, status)
    except Exception:
        logging.exception("Siklus ingestion gagal, akan dicoba lagi pada jadwal berikutnya.")


if __name__ == "__main__":
    logging.info(
        "Scheduler dimulai. Interval: setiap %s menit. Tekan Ctrl+C untuk berhenti.",
        INGEST_INTERVAL_MINUTES,
    )
    job()  # jalankan sekali di awal supaya database langsung terisi
    schedule.every(INGEST_INTERVAL_MINUTES).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(15)
