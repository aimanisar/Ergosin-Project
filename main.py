#!/usr/bin/env python3
import streamlit as st
import pandas as pd
from config import SITES
from storage import load_cache, save_cache
from topic_visualization import show_topic_visualization
from workflow import scrape_all_sites, scrape_site_with_cache
from ui_theme import apply_theme

# --------------------------- Modern UI Styling ---------------------------
st.set_page_config(page_title="Competitive Intelligence Dashboard", layout="wide")

st.markdown("""
<style>

/* ===== General App Background ===== */
.stApp {
    background-color: #f8fafc; /* Softer neutral tone */
    color: #1e293b;
    font-family: "Inter", "Segoe UI", sans-serif;
}

/* ===== Page Headings ===== */
h1, .stMarkdown h1 {
    color: #0f172a !important;
    font-weight: 700 !important;
    letter-spacing: -0.5px;
}

h2, h3, .stMarkdown h2, .stMarkdown h3 {
    color: #1e293b !important;
    font-weight: 600 !important;
    margin-top: 1.2rem;
    margin-bottom: 0.8rem;
}

/* ===== Subtle Captions / Notes ===== */
.stCaption, .stMarkdown small, .st-emotion-cache-12fmjuu {
    color: #6b7280 !important;
    font-style: italic;
}

/* ===== Tabs Styling ===== */
.stTabs [role="tablist"] {
    border-bottom: 2px solid #e2e8f0;
    margin-bottom: 1rem;
}
.stTabs [role="tab"] {
    background-color: #f1f5f9;
    border-radius: 8px 8px 0 0;
    padding: 10px 22px;
    font-weight: 600;
    margin-right: 6px;
    color: #475569;
    transition: all 0.2s ease;
}
.stTabs [aria-selected="true"] {
    background-color: #ffffff !important;
    color: #2563eb !important;
    border: 1px solid #e2e8f0;
    border-bottom: 2px solid #ffffff !important;
    box-shadow: 0 -2px 6px rgba(37, 99, 235, 0.05);
}

/* ===== Metric Cards ===== */
[data-testid="stMetricValue"] {
    color: #2563eb !important;
    font-weight: 700 !important;
    font-size: 1.6rem !important;
}
[data-testid="stMetricLabel"] {
    color: #475569 !important;
    font-weight: 500 !important;
}

/* ===== Reusable Card Containers ===== */
.card {
    background-color: white;
    border-radius: 14px;
    padding: 1.2rem 1.6rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 3px 8px rgba(0,0,0,0.06);
    border: 1px solid #f1f5f9;
}

/* ===== Buttons ===== */
div.stButton > button {
    background-color: #2563eb;
    color: white;
    border-radius: 6px;
    font-weight: 600;
    padding: 0.5rem 1.2rem;
    border: none;
    transition: all 0.2s ease;
}
div.stButton > button:hover {
    background-color: #1d4ed8;
    transform: translateY(-1px);
    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.3);
}

/* ===== Tables / Dataframes ===== */
.stDataFrame, .stTable {
    border-radius: 10px;
    background-color: white;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    border: 1px solid #e2e8f0;
}

/* ===== Metric Section Spacing ===== */
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
    padding-left: 3rem !important;
    padding-right: 3rem !important;
}

/* ===== Section Headers / Icons ===== */
section h2::before {
    content: "📊 ";
    font-size: 1.3rem;
}

</style>
""", unsafe_allow_html=True)

# Toggle theme mode
mode = st.sidebar.radio("🌓 Theme Mode", ["light", "dark"], horizontal=True)
apply_theme(mode)

# --------------------------- Competitor Row Renderer ---------------------------
def render_competitor_controls(sites, group_name):
    st.subheader(f"{group_name} Competitors List")

    # Extra CSS for buttons
    st.markdown("""
        <style>
        div.stButton > button {
            border-radius: 6px;
            font-weight: 600;
            padding: 0.4rem 1rem;
            transition: all 0.2s ease;
            width: 100%;
        }
        .scrape-btn {
            background-color: #16a34a !important;
            color: white !important;
        }
        .terminate-btn {
            background-color: #dc2626 !important;
            color: white !important;
        }
        .open-btn {
            background-color: #2563eb !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

    for i, site in enumerate(sites):
        url = site["url"]

        col1, col2, col3 = st.columns([6, 3, 2], gap="medium")

        with col1:
            st.markdown(f"🌐 [{url}]({url})")

<<<<<<< Updated upstream

st.caption("Terminate stops after the current page. Scrape ALL runs sites in order.")


# ------------------------ Data Status & Downloads ------------------------
with st.expander("Data status & downloads", expanded=False):
    try:
        df = load_cache()
        if not df.empty:
            st.write(f"**Data** — {df.shape[0]} rows")
            
            # Add cleanup button
            col1, col2 = st.columns([1, 1])
            with col1:
                st.download_button(
                    "⬇️ Download CSV",
                    df.to_csv(index=False).encode("utf-8"),
                    file_name="scraped_data.csv",
                    mime="text/csv",
                    key="dl_data"
                )
            with col2:
                if st.button("🧹 Clean Duplicates", key="cleanup_duplicates"):
                    from milvus_storage import get_milvus_storage
                    milvus_storage = get_milvus_storage()
                    milvus_storage.cleanup_duplicates()
                    st.rerun()
        else:
            st.info("No data available yet.")
    except Exception as e:
        st.error(f"Error loading data: {e}")
=======
        with col2:
            action = st.selectbox(
                "Choose action",
                ["🟢 Scrape", "🔴 Terminate", "🔵 Open"],
                key=f"action_{group_name}_{i}",
                label_visibility="collapsed"
            )

        with col3:
            if action == "🟢 Scrape":
                if st.button("Scrape", key=f"scrape_{group_name}_{i}"):
                    with st.spinner(f"Scraping {url}…"):
                        updated_df = scrape_site_with_cache(url)
                        save_cache(updated_df)
                    st.success(f"✅ Done scraping {url}")
                st.markdown(
                    "<style>div[data-testid='stButton'] button {background-color:#16a34a !important; color:white !important;}</style>",
                    unsafe_allow_html=True
                )

            elif action == "🔴 Terminate":
                if st.button("Terminate", key=f"terminate_{group_name}_{i}"):
                    st.session_state["cancel_scrape"] = True
                    st.warning(f"Termination requested for {url}")
                st.markdown(
                    "<style>div[data-testid='stButton'] button {background-color:red !important; color:white !important;}</style>",
                    unsafe_allow_html=True
                )

            elif action == "🔵 Open":
                st.link_button("Open", url)
                st.markdown(
                    "<style>div[data-testid='stButton'] a button {background-color:#2563eb !important; color:white !important;}</style>",
                    unsafe_allow_html=True
                )
>>>>>>> Stashed changes


# --------------------------- Header ---------------------------
st.markdown("""
<div style="background: linear-gradient(90deg, #2563eb, #9333ea);
            padding: 1.5rem 2rem; 
            border-radius: 12px; 
            color: white; 
            margin-bottom: 25px;">   <!-- 👈 gap added -->
    <h1 style="margin:0; font-size:2rem;">📊 Competitive Intelligence Dashboard</h1>
    <p style="margin:0.5rem 0 0; font-size:1rem;">
        Track, Analyze & Visualize competitor insights.
    </p>
</div>
""", unsafe_allow_html=True)

# --------------------------- Tabs ---------------------------
tab_close, tab_international = st.tabs(
    ["Close Competitors", "International Competitors"]
)

# --------------------------- Close Competitors ---------------------------
with tab_close:
    # st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Close Competitors Overview")
    st.caption("Detailed analysis of close competitors (services + topics)")

    close_sites = [s for s in SITES if s["type"] == "competitor_close"]
    if close_sites:
        render_competitor_controls(close_sites, "Close")

    df = load_cache()
    if not df.empty:
        show_topic_visualization(df, competitor_type="close", mode=mode)
    else:
        st.info("⚠️ No data available yet. Run scraper first.")

    st.markdown('</div>', unsafe_allow_html=True)

# --------------------------- International Competitors ---------------------------
with tab_international:
    # st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("International Competitors Overview")
    st.caption("Analysis of international competitors (topics + general insights)")

    intl_sites = [s for s in SITES if s["type"] == "competitor_international"]
    if intl_sites:
        render_competitor_controls(intl_sites, "International")

    df = load_cache()
    if not df.empty:
        show_topic_visualization(df, competitor_type="international")
    else:
        st.info("⚠️ No data available yet. Run scraper first.")

    st.markdown('</div>', unsafe_allow_html=True)
