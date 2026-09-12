"""
main.py
========
Entry point aplikasi Streamlit. File ini SENGAJA dibuat tipis -- hanya
mengurus layout (sidebar, header, tabs) dan mendelegasikan konten setiap
tab ke modul di app/views/. Semua data dibaca dari database (read-only);
TIDAK ADA pemanggilan API eksternal di sini, karena pengambilan data
dilakukan oleh proses ingestion terpisah (lihat app/data/ingestion.py
dan scripts/ingest_once.py).

Jalankan dengan:
    streamlit run app/main.py
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from app.config import CITIES, DEFAULT_CITY, CACHE_TTL_SECONDS, OPENWEATHER_API_KEY
from app.database import init_db, get_readings, get_row_count
from app.styles import inject_css, apply_plotly_theme, metric_card
from app.utils.aqi import classify_pm25
from app.views import dashboard, prediction, weather_analysis, time_series, about

st.set_page_config(
    page_title="Prediksi Kualitas Udara PM2.5",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
apply_plotly_theme()
init_db()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Memuat data dari database…")
def load_data(city: str, days: int) -> pd.DataFrame:
    df = get_readings(city, days=days)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def main():
    # ---------------------------------------------------------------- Sidebar
    with st.sidebar:
        st.header("⚙️ Konfigurasi")

        city = st.selectbox("Pilih Kota:", list(CITIES.keys()), index=list(CITIES.keys()).index(DEFAULT_CITY))
        model_choice = st.selectbox("Algoritma Prediksi:", ["LSTM", "Prophet", "Kedua Model"], index=2)
        pred_days = st.slider("Jumlah Hari Prediksi:", min_value=7, max_value=90, value=30)
        analysis_days = st.slider("Rentang Data Historis (hari):", min_value=7, max_value=365, value=90)

        st.markdown("---")
        st.markdown("### 📊 Kategori ISPU (PM2.5)")
        st.info(
            "🟢 **Baik**: 0–15,5 µg/m³\n\n"
            "🟡 **Sedang**: 15,6–55,4 µg/m³\n\n"
            "🟠 **Tidak Sehat**: 55,5–150,4 µg/m³\n\n"
            "🔴 **Sangat Tidak Sehat**: 150,5–250,4 µg/m³\n\n"
            "⚫ **Berbahaya**: > 250,5 µg/m³"
        )

        st.markdown("---")
        st.markdown("### 🗄️ Status Database")
        total_rows = get_row_count()
        st.caption(f"Total {total_rows:,} baris tersimpan (seluruh kota)")
        if not OPENWEATHER_API_KEY:
            st.warning("`OPENWEATHER_API_KEY` belum diset — ingestion tidak akan berjalan. Lihat README.md.")

    df = load_data(city, analysis_days)

    # ---------------------------------------------------------------- Header
    if df.empty:
        st.markdown(
            '<div class="app-header"><h1>🌫️ Prediksi Kualitas Udara PM2.5</h1>'
            '<p>Data real-time · LSTM &amp; Prophet · Indonesia</p></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="warn-box">⚠️ Belum ada data untuk <b>{}</b> di database. '
            "Jalankan langkah berikut dari terminal (lihat README.md untuk detail lengkap):"
            "<br><br>"
            "1. <code>python scripts/init_db.py</code><br>"
            "2. Isi <code>OPENWEATHER_API_KEY</code> di file <code>.env</code><br>"
            "3. <code>python scripts/seed_historical.py --days 90</code> (mengisi data historis)<br>"
            "4. <code>python scripts/ingest_once.py</code> (mengisi data terkini, lalu jadwalkan lewat cron)<br>"
            "5. <code>python scripts/train_models.py</code> (melatih model prediksi)"
            "</div>".format(city),
            unsafe_allow_html=True,
        )
        return

    latest = df.iloc[-1]
    cat = classify_pm25(latest["pm2_5"])
    last_updated = latest["timestamp"]
    minutes_ago = int((datetime.utcnow() - last_updated).total_seconds() / 60)

    st.markdown(
        f"""
        <div class="app-header">
            <h1>🌫️ Prediksi Kualitas Udara PM2.5</h1>
            <p>Data real-time dari OpenWeatherMap · Model LSTM &amp; Prophet · {city}, {CITIES[city]['province']}</p>
            <div class="live-badge"><span class="live-dot"></span> Data terakhir {minutes_ago} menit lalu ({last_updated.strftime('%d %b %Y, %H:%M')} UTC)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------------- Top metrics
    recent = df[df["timestamp"] >= df["timestamp"].max() - pd.Timedelta(days=min(analysis_days, 30))]
    trend_ref_idx = max(0, len(df) - 30)
    trend_30 = latest["pm2_5"] - df.iloc[trend_ref_idx]["pm2_5"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card("PM2.5 Terkini", f"{latest['pm2_5']:.1f} µg/m³", f"{cat['emoji']} {cat['label']}"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("Rata-rata Periode Ini", f"{recent['pm2_5'].mean():.1f} µg/m³", f"{analysis_days} hari terakhir"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("Level Tertinggi", f"{recent['pm2_5'].max():.1f} µg/m³", "dalam periode ini"), unsafe_allow_html=True)
    with c4:
        arrow = "↗️ naik" if trend_30 > 0 else "↘️ turun"
        st.markdown(metric_card("Tren", f"{trend_30:+.1f} µg/m³", f"{arrow} dibanding ~30 titik data lalu"), unsafe_allow_html=True)

    st.write("")

    # ---------------------------------------------------------------- Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard Utama", "🔮 Prediksi", "🌤️ Analisis Cuaca", "📈 Time Series", "ℹ️ Tentang",
    ])
    with tab1:
        dashboard.render(df, city)
    with tab2:
        prediction.render(df, city, model_choice, pred_days)
    with tab3:
        weather_analysis.render(df, city)
    with tab4:
        time_series.render(df, city)
    with tab5:
        about.render(df, city)

    st.markdown("---")
    st.caption(
        "**Prediksi Kualitas Udara PM2.5** · Data nyata OpenWeatherMap · Model LSTM & Prophet · "
        f"© {datetime.now().year}"
    )


if __name__ == "__main__":
    main()
