"""
database.py
============
Lapisan database berbasis SQLAlchemy. Skema ini dirancang agar proses
ingestion (scripts/ingest_once.py, dijalankan lewat cron / GitHub Actions)
dan aplikasi Streamlit (app/main.py, mode baca-saja) sama-sama bisa
mengakses data yang sama tanpa perlu membuka web app terlebih dahulu.

Alur data:
    [OpenWeatherMap API] --> ingestion.py --> tabel air_quality_readings
    tabel air_quality_readings --> Streamlit app (read-only, ter-cache)

Mendukung SQLite (default, lokal) maupun Postgres (set DATABASE_URL,
cocok untuk deployment cloud di mana ingestion dijalankan via GitHub
Actions terjadwal alih-alih cron lokal).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

Base = declarative_base()


class AirQualityReading(Base):
    """Satu baris = satu pengukuran kualitas udara + cuaca untuk 1 kota pada 1 waktu."""

    __tablename__ = "air_quality_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)  # waktu pengukuran (UTC)

    # Polutan (µg/m³), dari OpenWeatherMap Air Pollution API
    pm2_5 = Column(Float, nullable=False)
    pm10 = Column(Float, nullable=True)
    no2 = Column(Float, nullable=True)
    so2 = Column(Float, nullable=True)
    o3 = Column(Float, nullable=True)
    co = Column(Float, nullable=True)

    # Cuaca, dari OpenWeatherMap Current Weather API
    temperature = Column(Float, nullable=True)   # °C
    humidity = Column(Float, nullable=True)       # %
    wind_speed = Column(Float, nullable=True)     # m/s
    rainfall = Column(Float, nullable=True)        # mm (curah hujan 1 jam terakhir)

    source = Column(String(30), default="openweathermap")
    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("city", "timestamp", name="uq_city_timestamp"),
    )


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
        _engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
    return _engine


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    return _SessionLocal()


def init_db() -> None:
    """Membuat seluruh tabel jika belum ada. Aman dipanggil berkali-kali."""
    Base.metadata.create_all(get_engine())


def upsert_reading(row: dict) -> bool:
    """
    Menyimpan satu baris pengukuran. Jika kombinasi (city, timestamp) sudah
    ada, baris dilewati (idempotent) -- penting karena scheduler/cron bisa
    saja berjalan lebih dari sekali untuk jam yang sama.

    Mengembalikan True jika baris baru disimpan, False jika dilewati/duplikat.
    """
    session = get_session()
    try:
        exists = session.execute(
            select(AirQualityReading.id).where(
                AirQualityReading.city == row["city"],
                AirQualityReading.timestamp == row["timestamp"],
            )
        ).first()
        if exists:
            return False

        reading = AirQualityReading(**row)
        session.add(reading)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def bulk_upsert_readings(rows: list[dict]) -> int:
    """Menyimpan banyak baris sekaligus (dipakai saat backfill historis). Mengembalikan jumlah baris baru."""
    inserted = 0
    for row in rows:
        if upsert_reading(row):
            inserted += 1
    return inserted


def get_readings(city: str, days: Optional[int] = None) -> pd.DataFrame:
    """Mengambil data pengukuran untuk satu kota sebagai DataFrame, diurutkan berdasarkan waktu."""
    session = get_session()
    try:
        query = select(AirQualityReading).where(AirQualityReading.city == city)
        if days is not None:
            cutoff = datetime.utcnow() - pd.Timedelta(days=days)
            query = query.where(AirQualityReading.timestamp >= cutoff)
        query = query.order_by(AirQualityReading.timestamp.asc())

        rows = session.execute(query).scalars().all()
        if not rows:
            return pd.DataFrame(
                columns=[
                    "id", "city", "timestamp", "pm2_5", "pm10", "no2", "so2",
                    "o3", "co", "temperature", "humidity", "wind_speed",
                    "rainfall", "source", "fetched_at",
                ]
            )
        data = [
            {c.name: getattr(r, c.name) for c in AirQualityReading.__table__.columns}
            for r in rows
        ]
        return pd.DataFrame(data)
    finally:
        session.close()


def get_latest_reading(city: str) -> Optional[dict]:
    session = get_session()
    try:
        row = session.execute(
            select(AirQualityReading)
            .where(AirQualityReading.city == city)
            .order_by(AirQualityReading.timestamp.desc())
            .limit(1)
        ).scalars().first()
        if row is None:
            return None
        return {c.name: getattr(row, c.name) for c in AirQualityReading.__table__.columns}
    finally:
        session.close()


def get_available_cities() -> list[str]:
    session = get_session()
    try:
        rows = session.execute(select(AirQualityReading.city).distinct()).scalars().all()
        return sorted(rows)
    finally:
        session.close()


def get_row_count(city: Optional[str] = None) -> int:
    session = get_session()
    try:
        query = select(AirQualityReading.id)
        if city:
            query = query.where(AirQualityReading.city == city)
        return len(session.execute(query).all())
    finally:
        session.close()
