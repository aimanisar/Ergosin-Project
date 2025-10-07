import streamlit as st

def apply_theme(mode="light"):
    """Apply a professional Streamlit theme (light or dark mode)."""

    # Define color palettes
    light = {
        "bg": "#f8fafc",
        "text": "#1e293b",
        "accent": "#2563eb",
        "subtext": "#475569",
        "card": "#ffffff",
        "border": "#e2e8f0"
    }

    dark = {
        "bg": "#0f172a",
        "text": "#e2e8f0",
        "accent": "#60a5fa",
        "subtext": "#94a3b8",
        "card": "#1e293b",
        "border": "#334155"
    }

    # Choose palette
    theme = light if mode == "light" else dark

    # Apply CSS
    st.markdown(f"""
    <style>
    /* ===== Global Background ===== */
    .stApp {{
        background-color: {theme["bg"]};
        color: {theme["text"]};
        font-family: "Inter", "Segoe UI", sans-serif;
    }}

    /* ===== Titles ===== */
    h1, .stMarkdown h1 {{
        color: {theme["text"]} !important;
        font-weight: 700 !important;
    }}
    h2, h3, .stMarkdown h2, .stMarkdown h3 {{
        color: {theme["subtext"]} !important;
        font-weight: 600 !important;
    }}

    /* ===== Tabs ===== */
    .stTabs [role="tablist"] {{
        border-bottom: 2px solid {theme["border"]};
        margin-bottom: 1rem;
    }}
    .stTabs [role="tab"] {{
        background-color: {theme["card"]};
        border-radius: 8px 8px 0 0;
        padding: 10px 22px;
        font-weight: 600;
        margin-right: 6px;
        color: {theme["subtext"]};
        transition: all 0.2s ease;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {theme["bg"]} !important;
        color: {theme["accent"]} !important;
        border: 1px solid {theme["border"]};
        border-bottom: 2px solid {theme["bg"]} !important;
        box-shadow: 0 -2px 6px rgba(0,0,0,0.08);
    }}

    /* ===== Cards ===== */
    .card {{
        background-color: {theme["card"]};
        border-radius: 14px;
        padding: 1.2rem 1.6rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 3px 8px rgba(0,0,0,0.08);
        border: 1px solid {theme["border"]};
    }}

    /* ===== Metric Colors ===== */
    [data-testid="stMetricValue"] {{
        color: {theme["accent"]} !important;
        font-weight: 700 !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {theme["subtext"]} !important;
    }}

    /* ===== Buttons ===== */
    div.stButton > button {{
        background-color: {theme["accent"]};
        color: white;
        border-radius: 6px;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
        border: none;
        transition: all 0.2s ease;
    }}
    div.stButton > button:hover {{
        background-color: #1d4ed8;
        transform: translateY(-1px);
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.3);
    }}

    /* ===== Data Table ===== */
    .stDataFrame, .stTable {{
        border-radius: 10px;
        background-color: {theme["card"]};
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        border: 1px solid {theme["border"]};
    }}
    </style>
    """, unsafe_allow_html=True)


def apply_plotly_theme(fig, mode="light"):
    """Apply Plotly theme to match Streamlit UI theme"""
    if mode == "dark":
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e293b",
            plot_bgcolor="#1e293b",
            font=dict(color="#e2e8f0", size=13),
            legend=dict(bgcolor="#1e293b", font=dict(color="#e2e8f0")),
        )
    else:
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font=dict(color="#1e293b", size=13),
            legend=dict(bgcolor="#ffffff", font=dict(color="#1e293b")),
        )
    return fig
