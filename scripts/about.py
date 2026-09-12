"""views/about.py -- Tab "Tentang": penjelasan aplikasi, metodologi, dan cara kerja ingestion real-time."""
import pandas as pd
import streamlit as st

from app.database import get_row_count
from app.config import INGEST_INTERVAL_MINUTES


def render(df: pd.DataFrame, city: str):
    st.markdown('<div class="section-title">ℹ️ Tentang Aplikasi</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 📖 Ringkasan")
        st.markdown(
            "Aplikasi ini memantau dan memprediksi konsentrasi **PM2.5** di kota-kota besar "
            "Indonesia menggunakan data **nyata** dari OpenWeatherMap Air Pollution API, "
            "disimpan ke database, dan diprediksi dengan model **LSTM** dan **Prophet** "
            "yang benar-benar dilatih dari data historis (bukan simulasi)."
        )

        st.markdown("##### 🔄 Alur Data Real-Time")
        st.markdown(
            "```\n"
            "OpenWeatherMap API\n"
            "        │  (cron / GitHub Actions, setiap "
            f"{INGEST_INTERVAL_MINUTES} menit)\n"
            "        ▼\n"
            "scripts/ingest_once.py\n"
            "        ▼\n"
            "   Database (SQLite / Postgres)\n"
            "        ▼\n"
            "  Dashboard Streamlit (baca saja, ter-cache)\n"
            "```"
        )
        st.markdown(
            '<div class="info-box">Proses ingestion berjalan <b>independen</b> dari web app. '
            "Database terisi terus meskipun tidak ada yang membuka dashboard -- dashboard hanya "
            "membaca data yang sudah tersedia.</div>",
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("##### 🎯 Metodologi Model")
        st.markdown(
            "**1. LSTM (Long Short-Term Memory)**\n"
            "- Ditrain dari rata-rata PM2.5 harian dengan window 14 hari\n"
            "- Cocok menangkap dependency temporal jangka panjang\n\n"
            "**2. Prophet (Meta/Facebook)**\n"
            "- Menangkap tren & musiman (mingguan/tahunan) secara eksplisit\n"
            "- Robust terhadap data yang bolong"
        )

        st.markdown("##### 🌫️ Kategori ISPU (PM2.5, Permen LHK No. 14/2020)")
        st.markdown(
            "| Kategori | Rentang (µg/m³) |\n"
            "|---|---|\n"
            "| 🟢 Baik | 0 – 15,5 |\n"
            "| 🟡 Sedang | 15,6 – 55,4 |\n"
            "| 🟠 Tidak Sehat | 55,5 – 150,4 |\n"
            "| 🔴 Sangat Tidak Sehat | 150,5 – 250,4 |\n"
            "| ⚫ Berbahaya | > 250,5 |"
        )

    st.markdown("---")
    st.markdown("##### 📥 Unduh Data")
    c1, c2 = st.columns(2)
    with c1:
        csv = df.to_csv(index=False)
        st.download_button(
            "📊 Unduh Data Historis (CSV)", csv,
            file_name=f"data_pm25_{city}.csv", mime="text/csv", use_container_width=True,
        )
    with c2:
        st.metric("Total baris di database untuk kota ini", f"{get_row_count(city):,}")

    st.markdown("---")
    st.caption(
        "**Prediksi Kualitas Udara PM2.5** · Data: OpenWeatherMap Air Pollution & Weather API · "
        "Model: LSTM & Prophet (dilatih dari data nyata) · Kategori: ISPU PermenLHK No.14/2020"
    )
