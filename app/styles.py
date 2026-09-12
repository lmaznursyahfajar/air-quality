"""
styles.py
==========
CSS kustom + template Plotly terpusat, supaya seluruh halaman (views/*.py)
punya tampilan yang konsisten dan terlihat profesional.
"""
import streamlit as st
import plotly.io as pio
import plotly.graph_objects as go

PRIMARY = "#2563eb"
PRIMARY_DARK = "#1e3a8a"
ACCENT = "#0ea5e9"
BG_CARD = "#ffffff"
TEXT_MUTED = "#64748b"

CUSTOM_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    /* ---------- Header ---------- */
    .app-header {{
        background: linear-gradient(135deg, {PRIMARY_DARK} 0%, {PRIMARY} 55%, {ACCENT} 100%);
        padding: 2rem 2.5rem;
        border-radius: 18px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px rgba(37, 99, 235, 0.25);
    }}
    .app-header h1 {{
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.02em;
    }}
    .app-header p {{
        font-size: 0.95rem;
        opacity: 0.9;
        margin-top: 0.4rem;
        margin-bottom: 0;
    }}
    .live-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255,255,255,0.15);
        border: 1px solid rgba(255,255,255,0.3);
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-top: 0.75rem;
    }}
    .live-dot {{
        width: 8px; height: 8px; border-radius: 50%;
        background: #4ade80;
        box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.7);
        animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.6); }}
        70% {{ box-shadow: 0 0 0 8px rgba(74, 222, 128, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(74, 222, 128, 0); }}
    }}

    /* ---------- Section headers ---------- */
    .section-title {{
        font-size: 1.15rem;
        font-weight: 700;
        color: #0f172a;
        margin: 1.6rem 0 0.9rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e2e8f0;
    }}

    /* ---------- Metric / status cards ---------- */
    .metric-card {{
        background: {BG_CARD};
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    }}
    .metric-label {{
        font-size: 0.78rem;
        color: {TEXT_MUTED};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }}
    .metric-value {{
        font-size: 1.7rem;
        font-weight: 800;
        color: #0f172a;
        margin-top: 0.15rem;
    }}
    .metric-sub {{
        font-size: 0.82rem;
        color: {TEXT_MUTED};
        margin-top: 0.2rem;
    }}

    .status-card {{
        border-radius: 16px;
        padding: 1.4rem 1.6rem;
        color: white;
        text-align: center;
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    }}
    .status-card h2 {{
        margin: 0.2rem 0;
        font-size: 1.6rem;
        font-weight: 800;
    }}
    .status-card p {{
        margin: 0;
        opacity: 0.95;
    }}

    .info-box {{
        background: #eff6ff;
        border-left: 4px solid {PRIMARY};
        padding: 0.9rem 1.1rem;
        border-radius: 10px;
        font-size: 0.9rem;
        color: #1e3a8a;
    }}
    .warn-box {{
        background: #fff7ed;
        border-left: 4px solid #f97316;
        padding: 0.9rem 1.1rem;
        border-radius: 10px;
        font-size: 0.9rem;
        color: #7c2d12;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: #f8fafc;
    }}

    footer {{visibility: hidden;}}
    #MainMenu {{visibility: hidden;}}
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def apply_plotly_theme():
    """Template Plotly kustom dipakai di seluruh chart agar konsisten dengan tema web."""
    pio.templates["pm25_theme"] = go.layout.Template(
        layout=go.Layout(
            font=dict(family="Inter, sans-serif", color="#0f172a"),
            colorway=[PRIMARY, "#f97316", "#22c55e", "#a855f7", "#ef4444", "#0ea5e9"],
            paper_bgcolor="white",
            plot_bgcolor="white",
            title=dict(font=dict(size=16, color="#0f172a")),
            xaxis=dict(gridcolor="#f1f5f9", zerolinecolor="#e2e8f0"),
            yaxis=dict(gridcolor="#f1f5f9", zerolinecolor="#e2e8f0"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            margin=dict(t=60, l=40, r=30, b=40),
        )
    )
    pio.templates.default = "pm25_theme"


def metric_card(label: str, value: str, sub: str = "") -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>
    """


def status_card(label: str, value: str, color: str, emoji: str, sub: str = "") -> str:
    return f"""
    <div class="status-card" style="background: linear-gradient(135deg, {color}cc, {color});">
        <p>Status Kualitas Udara (ISPU)</p>
        <h2>{emoji} {label}</h2>
        <p>{value}{(' · ' + sub) if sub else ''}</p>
    </div>
    """
