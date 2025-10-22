#!/usr/bin/env python3
import time
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from config import SITES
from embeddings import GlobalSearchEngine
from storage import load_cache, save_cache
from topic_visualization import show_topic_visualization
from ui_theme import apply_theme
from workflow import scrape_all_sites, scrape_site_with_cache
from storage import load_cache


@st.cache_data(show_spinner=False, hash_funcs={list: lambda _: None})
def get_cached_data():
    """Load cached dataframe from Milvus (cached for performance)."""
    return load_cache()

@st.cache_resource(show_spinner=False)
def get_search_engine(df):
    """Build and cache search engine index."""
    engine = GlobalSearchEngine()
    engine.build_index_from_dataframe(df)
    return engine
# --------------------------------------------------------------------
# PAGE CONFIG & THEME
# --------------------------------------------------------------------
st.set_page_config(page_title="Competitive Intelligence Dashboard",
                   layout="wide")

st.markdown("""
<style>
/* ===== General App Background ===== */
.stApp {
    background-color: #f8fafc;
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
    background: linear-gradient(90deg, #2563eb, #9333ea);
    color: white !important;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.55rem 1.3rem;
    border: none;
    transition: all 0.25s ease;
    width: 100%;
    box-shadow: 0 2px 4px rgba(0,0,0,0.15);
}
div.stButton > button:hover {
    background: linear-gradient(90deg, #1d4ed8, #7e22ce);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(147,51,234,0.4);
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

mode = st.sidebar.radio("🌓 Theme Mode", ["light", "dark"], horizontal=True)
apply_theme(mode)

# --------------------------------------------------------------------
# COMPETITOR ROW RENDERER
# --------------------------------------------------------------------

def render_competitor_controls(sites, group_name):
    """Render competitor cards and scrape buttons."""
    st.subheader(f"{group_name} Competitors List")

    st.markdown("""
        <style>
        div.stButton > button {
            border-radius: 6px;
            font-weight: 600;
            padding: 0.4rem 1rem;
            transition: all 0.2s ease;
            background-color: #16a34a !important;
            color: white !important;
            border: none;
            width: 100%;
        }
        div.stButton > button:hover {
            background-color: #15803d !important;
            transform: translateY(-1px);
            box-shadow: 0 2px 6px rgba(22, 163, 74, 0.4);
        }
        </style>
    """, unsafe_allow_html=True)

    for i, site in enumerate(sites):
        name = site.get("name") or site["url"].split("//")[-1].split("/")[0]
        url = site["url"]

        col1, col2 = st.columns([8, 2], gap="medium")
        with col1:
            st.markdown(
                f"🌐 <a href='{url}' target='_blank' "
                f"style='color:#60a5fa; font-weight:600; "
                f"text-decoration:none; font-size:1.05rem;'>{name}</a>",
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("Scrape", key=f"scrape_{group_name}_{i}"):
                with st.spinner(f"Scraping {name} ({url})..."):
                    updated_df = scrape_site_with_cache(url)
                    save_cache(updated_df)
                st.success(f"✅ Done scraping {name}")

# --------------------------------------------------------------------
# HEADER WITH METRICS
# --------------------------------------------------------------------
df_cache = load_cache()

total_competitors = len(
    set(df_cache["website"].unique())
) if not df_cache.empty else len(SITES)

total_topics = (
    len(
        pd.Series(
            df_cache["topics"].dropna().apply(
                lambda x: [t.strip() for t in str(x).split(",")]
            )
        ).explode().unique()
    )
    if not df_cache.empty else 0
)

last_updated = "recently"
if not df_cache.empty and "last_scraped" in df_cache.columns:
    try:
        last_time = pd.to_datetime(df_cache["last_scraped"]).max()
        if last_time is not pd.NaT:
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)
            days_ago = (datetime.now(timezone.utc) - last_time).days
            last_updated = f"{days_ago} day{'s' if days_ago != 1 else ''} ago"
    except Exception:
        last_updated = "recently"

st.markdown(f"""
    <div>         
# <div style="background: linear-gradient(90deg, #2563eb, #9333ea);
#             padding: 1.5rem 2rem;
#             border-radius: 12px;
#             color: white;
#             margin-bottom: 25px;">
    <h1 style="margin:0; font-size:2rem;">
         Competitive Intelligence Dashboard
    </h1>
    <p style="margin:0.5rem 0 1rem; font-size:1rem;">
        Track, Analyze & Visualize competitor insights.
    </p>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------
# 🌐 GLOBAL SEARCH (Inline input with clear icon inside)
# --------------------------------------------------------------------
with st.expander("🔍 Global Search Across Scraped Content", expanded=False):

    # --- Custom Styling ---
    st.markdown("""
        <style>
        .search-wrapper {
            position: relative;
            width: 100%;
        }
        .search-input {
            width: 100%;
            padding: 0.55rem 2.3rem 0.55rem 0.8rem;
            border-radius: 8px;
            border: 1px solid #374151;
            background-color: #1f2937;
            color: #f3f4f6;
            font-size: 0.95rem;
            outline: none;
        }
        .search-input::placeholder {
            color: #9ca3af;
        }
        .clear-icon {
            position: absolute;
            right: 0.7rem;
            top: 50%;
            transform: translateY(-50%);
            cursor: pointer;
            font-size: 1.1rem;
            color: #d1d5db;
            transition: 0.2s;
            background: none;
            border: none;
        }
        .clear-icon:hover {
            color: #f9fafb;
            transform: translateY(-50%) scale(1.1);
        }
        .search-btn {
            background: linear-gradient(90deg, #6366f1, #9333ea);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.55rem 1.2rem;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .search-btn:hover {
            background: linear-gradient(90deg, #818cf8, #a78bfa);
            transform: translateY(-1px);
            box-shadow: 0 2px 6px rgba(99,102,241,0.4);
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Layout: Input + Button ---
    col1, col2 = st.columns([7.5, 2.5])
    with col1:
        query_placeholder = "Type to search competitors' content..."
        query = st.text_input(
            "Search query",
            value=st.session_state.get("global_search_q", ""),
            placeholder=query_placeholder,
            label_visibility="collapsed",
            key="global_search_q_box",
        )

        # Inject ❌ Clear button dynamically
        st.markdown("""
        <script>
        const inputBox = window.parent.document.querySelector('input[id^="global_search_q_box"]');
        if (inputBox && !window.clearIconInjected) {
            const clearBtn = document.createElement('button');
            clearBtn.innerText = '✕';
            clearBtn.className = 'clear-icon';
            clearBtn.onclick = function() {
                inputBox.value = '';
                const event = new Event('input', { bubbles: true });
                inputBox.dispatchEvent(event);
                window.parent.postMessage({ type: 'clearSearchLogs' }, '*');
            };
            inputBox.parentNode.classList.add('search-wrapper');
            inputBox.parentNode.appendChild(clearBtn);
            window.clearIconInjected = true;
        }
        </script>
        """, unsafe_allow_html=True)

    with col2:
        search_trigger = st.button("Search", key="search_button")

    # --- Load cached Milvus data once ---
    with st.spinner("🔄 Loading cached data from Milvus..."):
        df_cache = get_cached_data()
        if "search_engine" not in st.session_state:
            st.session_state["search_engine"] = get_search_engine(df_cache)
        engine = st.session_state["search_engine"]

    # --- Session states ---
    if "search_results" not in st.session_state:
        st.session_state["search_results"] = []
    if "last_query" not in st.session_state:
        st.session_state["last_query"] = ""

    # --- Handle Search ---
    if search_trigger:
        q = (query or "").strip()
        if not q:
            st.warning("Please enter a search term.")
            st.session_state["search_results"] = []
        else:
            with st.spinner("Searching embeddings..."):
                results = engine.query(q, top_k=15)
            st.session_state["search_results"] = results
            st.session_state["last_query"] = q

    # --- Display Logs within Dropdown ---
    results = st.session_state.get("search_results", [])
    q = st.session_state.get("last_query", "")

    if results:
        st.markdown(f"##### Results for: _{q}_")
        for meta, score in results:
            page_name = meta.get("page_name", "Untitled")
            url = meta.get("url", "#")
            chunk = meta.get("chunk_text", "")
            short_text = chunk[:400] + ("..." if len(chunk) > 400 else "")
            st.markdown(
                f"""
                <div style='padding:10px; border-radius:8px;
                            background-color:#1e293b; margin-bottom:10px;'>
                    <b style="color:#f9fafb;">{page_name}</b><br>
                    <a href="{url}" target="_blank" style="color:#60a5fa;">{url}</a><br>
                    <span style="font-size:12px; color:#9ca3af;">Relevance: {score:.3f}</span>
                    <p style='color:#d1d5db; margin-top:5px;'>{short_text}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    elif q and not results:
        st.info("No matches found.")


# --------------------------------------------------------------------
# SCRAPE ALL BUTTON + BASE WEBSITE SECTION (Side-by-Side)
# --------------------------------------------------------------------
st.markdown("""
<style>
.scrape-row {
    display: flex;
    justify-content: space-between;
    gap: 1.5rem;
    margin-bottom: 30px;
}

.scrape-card {
    flex: 1;
    background: linear-gradient(135deg, #1e3a8a, #312e81);
    color: white;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
    text-align: center;
    min-height: 170px;  /* reduced height */
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.scrape-card h2 {
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}

.scrape-card p {
    font-size: 0.95rem;
    color: #c7d2fe;
    margin-bottom: 1rem;
}

/* Scrape Buttons */
.scrape-btn {
    background: linear-gradient(90deg, #16a34a, #15803d);
    color: white;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1.5rem;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.2s ease;
}
.scrape-btn:hover {
    background: linear-gradient(90deg, #22c55e, #16a34a);
    transform: translateY(-2px);
    box-shadow: 0 3px 10px rgba(22,163,74,0.4);
}

/* Darker variant for Ergosign */
.scrape-card.ergosign {
    background: linear-gradient(135deg, #1e40af, #3730a3);
}
.scrape-card a {
    color: #bfdbfe;
    text-decoration: none;
    font-weight: 500;
}
</style>

<div class="scrape-row">
  <!-- Left: Automated Web Scraping -->
  <div class="scrape-card">
    <h2>🚀 Automated Web Scraping</h2>
    <p>Fetch and update competitor insights directly from all websites.</p>
    <button class="scrape-btn" onclick="window.location.reload()">Scrape All Competitors</button>
  </div>

  <!-- Right: Base Website Ergosign -->
  <div class="scrape-card ergosign">
    <h2>🏠 Base Website – Ergosign</h2>
    <p><a href="https://www.ergosign.de/en/" target="_blank">ergosign.de/en</a></p>
    <button class="scrape-btn" id="ergosign_scrape">Scrape Ergosign</button>
  </div>
</div>
""", unsafe_allow_html=True)

# # --- Python backend for Ergosign scrape ---
# if st.button("🔄 Scrape Ergosign", key="scrape_ergosign_ui", use_container_width=False):
#     with st.spinner("Scraping Ergosign ..."):
#         updated_df = scrape_site_with_cache("https://www.ergosign.de/en/")
#         save_cache(updated_df)
#     st.success("✅ Ergosign updated successfully!")

# # --------------------------------------------------------------------
# # Ergosin Scrape BUTTON
# # --------------------------------------------------------------------
# st.subheader("Base Website – Ergosign")
# ergosign_url = "https://www.ergosign.de/en/"

# col1, col2 = st.columns([8, 2])
# with col1:
#     st.markdown(
#         f"<a href='{ergosign_url}' target='_blank' style='color:#2563eb;font-weight:600;text-decoration:none;'>ergosign.en</a>",
#         unsafe_allow_html=True,
#     )
# with col2:
#     if st.button("Scrape Ergosign", key="scrape_ergosign", use_container_width=True):
#         with st.spinner("Scraping Ergosign ..."):
#             updated_df = scrape_site_with_cache(ergosign_url)
#             save_cache(updated_df)
#         st.success("✅ Ergosign updated successfully!")


# --------------------------------------------------------------------
# SIDEBAR & MAIN CONTENT
# --------------------------------------------------------------------
st.sidebar.header("Competitor View")
view_option = st.sidebar.radio(
    "Select Competitor Group:",
    ("Close Competitors", "International Competitors")
)
st.sidebar.markdown("---")

if view_option == "Close Competitors":
    close_sites = [s for s in SITES if s["type"] == "competitor_close"]
    if close_sites:
        render_competitor_controls(close_sites, "Close")
    df = load_cache()
    if not df.empty:
        show_topic_visualization(df, competitor_type="close", mode=mode)
    else:
        st.info("⚠️ No data available yet. Run scraper first.")
else:
    intl_sites = [s for s in SITES if s["type"] == "competitor_international"]
    if intl_sites:
        render_competitor_controls(intl_sites, "International")
    df = load_cache()
    if not df.empty:
        show_topic_visualization(df, competitor_type="international", mode=mode)
    else:
        st.info("⚠️ No data available yet. Run scraper first.")
