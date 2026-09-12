"""views/weather_analysis.py -- Tab "Analisis Cuaca": korelasi PM2.5 dengan faktor cuaca."""
import pandas as pd
import plotly.express as px
import streamlit as st


WEATHER_FACTORS = [
    ("temperature", "Suhu", "°C", "🌡️"),
    ("humidity", "Kelembaban", "%", "💧"),
    ("wind_speed", "Kecepatan Angin", "m/s", "💨"),
    ("rainfall", "Curah Hujan", "mm", "🌧️"),
]


def render(df: pd.DataFrame, city: str):
    st.markdown('<div class="section-title">🌤️ Pengaruh Faktor Cuaca terhadap PM2.5</div>', unsafe_allow_html=True)

    weather_cols = [f[0] for f in WEATHER_FACTORS]
    available = [c for c in weather_cols if df[c].notna().sum() > 5]

    if not available:
        st.markdown(
            '<div class="warn-box">⚠️ Belum ada data cuaca yang cukup untuk kota ini. '
            'Data cuaca terisi otomatis begitu proses ingestion real-time berjalan '
            '(data hasil backfill historis hanya berisi polutan, bukan cuaca).</div>',
            unsafe_allow_html=True,
        )
        return

    corr_df = df[["pm2_5"] + available].dropna()
    if len(corr_df) < 5:
        st.info("Data cuaca masih terlalu sedikit untuk analisis korelasi yang bermakna.")
        return

    corr_matrix = corr_df.corr()

    col1, col2 = st.columns([1.1, 1])
    with col1:
        fig = px.imshow(
            corr_matrix, text_auto=".2f", aspect="auto",
            color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
            title="Matriks Korelasi",
        )
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### 📊 Dampak Faktor Cuaca terhadap PM2.5")
        for col, name, unit, icon in WEATHER_FACTORS:
            if col not in available:
                continue
            corr = corr_matrix.loc["pm2_5", col]
            c1, c2 = st.columns([1, 3])
            c1.metric(icon, f"{corr:+.2f}")
            direction = "berkorelasi positif" if corr > 0 else "berkorelasi negatif"
            c2.caption(f"{name} ({unit}) {direction} dengan PM2.5")

    st.markdown("##### 📈 Hubungan PM2.5 dengan Faktor Cuaca")
    cols = st.columns(2)
    for i, (col, name, unit, icon) in enumerate(WEATHER_FACTORS):
        if col not in available:
            continue
        with cols[i % 2]:
            fig = px.scatter(
                corr_df, x=col, y="pm2_5", trendline="ols",
                title=f"PM2.5 vs {name}",
                labels={col: f"{name} ({unit})", "pm2_5": "PM2.5 (µg/m³)"},
                color_discrete_sequence=["#2563eb"],
            )
            fig.update_layout(height=320)
            st.plotly_chart(fig, use_container_width=True)
