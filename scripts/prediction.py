"""views/prediction.py -- Tab "Prediksi": menjalankan model LSTM/Prophet yang SUDAH dilatih."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.ml import lstm_model, prophet_model
from app.utils.aqi import classify_pm25
from app.config import ISPU_BREAKPOINTS


def _get_prediction(model_choice: str, city: str, df: pd.DataFrame, pred_days: int):
    """Mengambil prediksi dari model yang sudah dilatih. Mengembalikan (dict_of_dataframes, list_pesan_error)."""
    results = {}
    errors = []

    if model_choice in ("LSTM", "Kedua Model"):
        try:
            results["LSTM"] = lstm_model.predict_future(city, df, pred_days)
        except Exception as exc:
            errors.append(f"**LSTM** belum bisa dipakai untuk {city}: {exc}")

    if model_choice in ("Prophet", "Kedua Model"):
        try:
            results["Prophet"] = prophet_model.predict_future(city, pred_days)
        except Exception as exc:
            errors.append(f"**Prophet** belum bisa dipakai untuk {city}: {exc}")

    return results, errors


def render(df: pd.DataFrame, city: str, model_choice: str, pred_days: int):
    st.markdown('<div class="section-title">🔮 Prediksi PM2.5</div>', unsafe_allow_html=True)

    results, errors = _get_prediction(model_choice, city, df, pred_days)

    for msg in errors:
        st.markdown(f'<div class="warn-box">⚠️ {msg}</div>', unsafe_allow_html=True)

    if not results:
        st.info(
            "Belum ada model terlatih yang bisa dipakai. Jalankan `python scripts/train_models.py` "
            "setelah data historis cukup (lihat tab **Tentang** untuk panduan lengkap)."
        )
        return

    recent = df.set_index("timestamp")["pm2_5"].resample("D").mean().reset_index()
    recent = recent.rename(columns={"timestamp": "date"})

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=recent["date"], y=recent["pm2_5"], name="Data Historis (rata-rata harian)",
        line=dict(color="#2563eb", width=3), opacity=0.85,
    ))
    colors = {"LSTM": "#ef4444", "Prophet": "#22c55e"}
    for model_name, pred_df in results.items():
        fig.add_trace(go.Scatter(
            x=pred_df["date"], y=pred_df["predicted_pm25"], name=f"Prediksi {model_name}",
            line=dict(color=colors.get(model_name, "#a855f7"), width=3, dash="dash"),
        ))
    for low, high, label, color, _ in ISPU_BREAKPOINTS[:-1]:
        fig.add_hline(y=high, line_dash="dot", line_color=color, opacity=0.5,
                      annotation_text=label, annotation_font_size=10)
    fig.update_layout(
        title=f"Prediksi PM2.5 — {city} ({model_choice})",
        xaxis_title="Tanggal", yaxis_title="PM2.5 (µg/m³)",
        height=480, showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Ringkasan
    if len(results) == 2:
        combined = results["LSTM"].copy()
        combined["predicted_pm25"] = (
            results["LSTM"]["predicted_pm25"].values + results["Prophet"]["predicted_pm25"].values
        ) / 2
        pred_data = combined
    else:
        pred_data = next(iter(results.values()))

    avg_pred = pred_data["predicted_pm25"].mean()
    max_pred = pred_data["predicted_pm25"].max()
    cat = classify_pm25(avg_pred)

    st.markdown("##### 📋 Ringkasan Prediksi")
    c1, c2, c3 = st.columns(3)
    c1.metric("Rata-rata Prediksi", f"{avg_pred:.1f} µg/m³")
    c2.metric("Perkiraan Puncak", f"{max_pred:.1f} µg/m³")
    c3.metric("Status Rata-rata", f"{cat['emoji']} {cat['label']}")

    st.markdown("##### 📅 Tabel Prediksi Harian")
    display_pred = pred_data.copy()
    display_pred["Status"] = display_pred["predicted_pm25"].apply(lambda x: classify_pm25(x)["label"])
    display_pred["date"] = display_pred["date"].dt.strftime("%Y-%m-%d")
    display_pred = display_pred.rename(columns={"predicted_pm25": "PM2.5 Prediksi (µg/m³)", "date": "Tanggal"})
    st.dataframe(display_pred[["Tanggal", "PM2.5 Prediksi (µg/m³)", "Status"]], use_container_width=True, hide_index=True)

    csv = display_pred.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Unduh Prediksi (CSV)", csv, file_name=f"prediksi_pm25_{city}.csv", mime="text/csv")
