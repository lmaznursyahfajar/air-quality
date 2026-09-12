#!/usr/bin/env python3
"""
scripts/ingest_once.py
========================
Satu kali siklus pengambilan data (semua kota) lalu keluar. Inilah script
yang membuat data "masuk sendiri ke database" TANPA perlu membuka web app
terlebih dahulu -- dijadwalkan lewat cron / systemd timer / Task Scheduler
/ GitHub Actions (lihat README.md bagian "Menjadwalkan Ingestion").

Contoh crontab (Linux/macOS), jalan tiap jam:
    0 * * * * cd /path/ke/pm25-dashboard && /path/ke/python scripts/ingest_once.py >> logs/ingest.log 2>&1

Exit code 0 = sukses (meski sebagian kota gagal, selama tidak ada exception fatal).
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.ingestion import fetch_and_store_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

if __name__ == "__main__":
    logging.info("=== Memulai siklus ingestion ===")
    summary = fetch_and_store_all()
    for city, status in summary.items():
        logging.info("%-12s -> %s", city, status)
    logging.info("=== Siklus ingestion selesai ===")
