"""views/dashboard.py -- Tab "Dashboard Utama": tren historis, distribusi, status saat ini."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.styles import status_card
from app.utils.aqi import classify_pm25, get_recommendation
from app.config import ISPU_BREAKPOINTS


def render(df: pd.DataFrame, city: str):
    st.markdown('<div class="section-title">📊 Tren &amp; Distribusi PM2.5</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.line(
            df, x="timestamp", y="pm2_5",
            title=f"Tren PM2.5 per Jam — {city}",
            labels={"pm2_5": "PM2.5 (µg/m³)", "timestamp": "Waktu"},
        )
        fig.update_traces(line=dict(width=2))
        for low, high, label, color, _ in ISPU_BREAKPOINTS[:-1]:
            fig.add_hline(y=high, line_dash="dash", line_color=color, opacity=0.6,
                          annotation_text=label, annotation_font_size=10)
        fig.update_layout(height=400, showlegend=False, xaxis=dict(rangeslider=dict(visible=True)))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.histogram(
            df, x="pm2_5", nbins=30,
            title=f"Distribusi PM2.5 — {city}",
            labels={"pm2_5": "PM2.5 (µg/m³)"},
            color_discrete_sequence=["#2563eb"],
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        daily = df.set_index("timestamp")["pm2_5"].resample("D").mean().reset_index()
        daily["day_name"] = daily["timestamp"].dt.strftime("%d %b")
        fig = px.bar(
            daily, x="day_name", y="pm2_5",
            title="Rata-rata PM2.5 Harian",
            labels={"pm2_5": "PM2.5 (µg/m³)", "day_name": "Tanggal"},
            color="pm2_5", color_continuous_scale=["#22c55e", "#eab308", "#f97316", "#ef4444"],
        )
        fig.update_layout(height=340, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        latest = df.iloc[-1]
        cat = classify_pm25(latest["pm2_5"])
        st.markdown(
            status_card(cat["label"], f"{latest['pm2_5']:.1f} µg/m³", cat["color"], cat["emoji"]),
            unsafe_allow_html=True,
        )
        st.markdown("##### 💡 Rekomendasi")
        rec = get_recommendation(cat["label"])
        if cat["level"] <= 1:
            st.success(rec)
        elif cat["level"] == 2:
            st.warning(rec)
        else:
            st.error(rec)

        st.caption(
            f"Data terakhir: {latest['timestamp'].strftime('%d %B %Y, %H:%M')} UTC · "
            f"sumber: {latest.get('source', 'openweathermap')}"
        )
