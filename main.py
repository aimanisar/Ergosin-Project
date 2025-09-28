#!/usr/bin/env python3
"""
Competitive Intelligence Dashboard
Professional website scraping and analysis platform for market research.

This module provides a Streamlit-based interface for:
- Automated website scraping
- AI-powered content analysis
- Competitive intelligence gathering
- Data visualization and insights
"""

import streamlit as st
import pandas as pd

from config import SITES
from storage import load_cache, save_cache
from workflow import scrape_all_sites, scrape_site_with_cache


# --------------------------- UI Styling ---------------------------
st.markdown("""
<style>
.block-container { max-width: 1100px !important; }
.toolbar .stButton>button { height: 48px; font-weight: 600; }
.site-card {
  border: 1px solid #eaeaea; border-radius: 14px; padding: 14px 16px;
  margin-bottom: 12px; background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}
.badge {
  display: inline-block; padding: 3px 8px; border-radius: 999px;
  font-size: 12px; font-weight: 600; letter-spacing: .2px;
  background: #eef2ff; color: #3b5bdb;
}
.badge.base { background:#e6fcf5; color:#087f5b; }
.badge.competitor { background:#fff1f0; color:#d64545; }
.action-col .stButton>button { width: 100%; height: 42px; }
.open-link a { font-weight: 600; text-decoration: none; }
.open-link a:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)


# --------------------------- Session State ---------------------------
if "cancel_scrape" not in st.session_state:
    st.session_state["cancel_scrape"] = False


# ---------------------------- Header ----------------------------
st.title("Automated Website Scraper (Raw + Topics)")


# ------------------------- Global Controls -------------------------
with st.container():
    c1, c2 = st.columns([6, 6], gap="small")
    with c1:
        if st.button("❌ Terminate", use_container_width=True):
            st.session_state["cancel_scrape"] = True
            st.warning("Termination requested. Will stop after the current page.")
    with c2:
        if st.button("🚀 Scrape ALL Websites", type="primary", use_container_width=True):
            scrape_all_sites()


st.caption("Terminate stops after the current page. Scrape ALL runs sites in order.")


# ------------------------ Data Status & Downloads ------------------------
with st.expander("Data status & downloads", expanded=False):
    try:
        df = load_cache()
        if not df.empty:
            st.write(f"**Data** — {df.shape[0]} rows")
            st.download_button(
                "⬇️ Download CSV",
                df.to_csv(index=False).encode("utf-8"),
                file_name="scraped_data.csv",
                mime="text/csv",
                key="dl_data"
            )
        else:
            st.info("No data available yet.")
    except Exception as e:
        st.error(f"Error loading data: {e}")


# ------------------------ Per-Site Scrape Controls ------------------------
st.subheader("Scrape Individual Websites")

for i, site in enumerate(SITES):
    site_url = site["url"].strip()
    site_type = site["type"]

    with st.container():
        st.markdown('<div class="site-card">', unsafe_allow_html=True)
        r1c1, r1c2, r1c3, r1c4 = st.columns([6, 2, 2, 2], gap="medium")

        # Left: URL + type badge
        with r1c1:
            st.markdown(f"**[{site_url}]({site_url})**")
            st.markdown(f'<span class="badge {site_type}">{site_type}</span>', unsafe_allow_html=True)

        # Scrape button
        with r1c2:
            if st.button("Scrape", key=f"scrape_{i}"):
                with st.spinner(f"Scraping {site_url}…"):
                    updated_df = scrape_site_with_cache(site_url)
                    save_cache(updated_df)
                st.success(f"✅ Done scraping {site_url}")

        # Terminate button
        with r1c3:
            if st.button("Terminate", key=f"term_{i}"):
                st.session_state["cancel_scrape"] = True
                st.warning("Termination requested for this site. Will stop after current page.")

        # Open link
        with r1c4:
            st.markdown(f'<a href="{site_url}" target="_blank">Open</a>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


# ------------------------ Visualization Section ------------------------
with st.expander("Topic Analysis & Comparison", expanded=False):
    try:
        df = load_cache()
        if not df.empty:
            try:
                from topic_visualization import show_topic_visualization
                show_topic_visualization()
            except Exception as e:
                st.error(f"Error loading visualizations: {e}")
        else:
            st.info("No data available for visualization. Please scrape some websites first.")
    except Exception as e:
        st.error(f"Error checking data: {e}")