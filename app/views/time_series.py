"""views/time_series.py -- Tab "Time Series": dekomposisi musiman sungguhan + perbandingan model."""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from app.ml.metrics import load_metrics


def render(df: pd.DataFrame, city: str):
    st.markdown('<div class="section-title">📈 Analisis Time Series</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 🎯 Dekomposisi Musiman (Trend / Seasonal / Residual)")
        daily = df.set_index("timestamp")["pm2_5"].resample("D").mean().dropna()

        if len(daily) < 14:
            st.info("Minimal 14 hari data harian diperlukan untuk dekomposisi musiman. "
                     "Biarkan ingestion berjalan lebih lama atau jalankan backfill historis.")
        else:
            try:
                from statsmodels.tsa.seasonal import seasonal_decompose
                period = 7 if len(daily) < 60 else min(365, len(daily) // 2)
                result = seasonal_decompose(daily, model="additive", period=period, extrapolate_trend="period")

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=daily.index, y=result.trend, name="Trend", line=dict(color="#ef4444")))
                fig.add_trace(go.Scatter(x=daily.index, y=result.seasonal, name="Musiman", line=dict(color="#2563eb")))
                fig.add_trace(go.Scatter(x=daily.index, y=result.resid, name="Residual", line=dict(color="#22c55e")))
                fig.update_layout(title=f"Dekomposisi PM2.5 Harian — {city}", height=400)
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.warning("Modul `statsmodels` belum terpasang. Jalankan: pip install statsmodels")

    with col2:
        st.markdown("##### 🤖 Perbandingan Performa Model")
        metrics = load_metrics(city)

        if not metrics:
            st.info(
                "Belum ada metrik model untuk kota ini. Jalankan `python scripts/train_models.py` "
                "-- MAE dan RMSE dihitung otomatis dari data validasi asli saat training."
            )
        else:
            rows = [{"Model": name, "MAE (µg/m³)": v["mae"], "RMSE (µg/m³)": v["rmse"]} for name, v in metrics.items()]
            comp_df = pd.DataFrame(rows)

            fig = px.bar(
                comp_df.melt(id_vars="Model", var_name="Metrik", value_name="Nilai"),
                x="Model", y="Nilai", color="Metrik", barmode="group",
                title="MAE & RMSE (lebih rendah = lebih baik)",
                color_discrete_map={"MAE (µg/m³)": "#2563eb", "RMSE (µg/m³)": "#f97316"},
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Dihitung dari data validasi/holdout asli saat training terakhir, bukan angka simulasi.")

    st.markdown("##### 📊 Data Mentah Terbaru")
    st.dataframe(
        df.sort_values("timestamp", ascending=False).head(50)[
            ["timestamp", "pm2_5", "pm10", "temperature", "humidity", "wind_speed", "rainfall"]
        ],
        use_container_width=True,
        hide_index=True,
    )
