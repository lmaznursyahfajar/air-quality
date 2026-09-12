#!/usr/bin/env python3
"""
scripts/init_db.py
====================
Membuat tabel database (sekali jalan). Jalankan ini pertama kali sebelum
apa pun yang lain:

    python scripts/init_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import init_db
from app.config import DATABASE_URL

if __name__ == "__main__":
    init_db()
    print(f"✅ Database siap di: {DATABASE_URL}")
