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
from topic_visualization import create_topic_network

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
    content: "";
    font-size: 1.3rem;
}
</style>
""", unsafe_allow_html=True)

# Apply uniform gradient card styling to specific containers so content renders inside
## Removed earlier per-user CSS block to simplify and unify styling

# Set dark mode as default
mode = "dark"
apply_theme(mode)
# --------------------------------------------------------------------
# Rounded card styling for the three scrape/metric boxes (dark mode)
# --------------------------------------------------------------------
card_bg = "#1e293b"
card_border = "#334155"
card_text = "#e2e8f0"

st.markdown(
    """
    <style>
    /* Unified card style for two boxes with gradient border */
    div[data-testid="stVerticalBlock"][data-key="card_scrape_all"],
    div[data-testid="stVerticalBlock"][data-key="card_ergosign"] {
        background: linear-gradient(145deg, #0f172a, #1e293b, #164e63) padding-box,
                    linear-gradient(90deg, #1e3a8a, #312e81, #164e63, #0d9488) border-box;
        border: 3px solid transparent;
        border-radius: 16px;
        padding: 2rem;
        min-height: 180px;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 1.5rem;
        box-shadow: 0 10px 26px rgba(0,0,0,0.20);
        color: #e5e7eb;
        text-align: center;
        position: relative;
        overflow: hidden;
        transition: all .2s ease;
        will-change: transform;
        margin-bottom: 1rem;
    }


    /* Ensure Streamlit's inner bordered wrapper also has equal height */
    div[data-testid="stVerticalBlock"][data-key="card_scrape_all"] > div:first-child,
    div[data-testid="stVerticalBlock"][data-key="card_ergosign"] > div:first-child {
        min-height: 100%;                  /* equal inner height */
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 10px;
        background: transparent;
    }

    /* Subtle hover lift and glow */
    div[data-testid="stVerticalBlock"][data-key="card_scrape_all"]:hover,
    div[data-testid="stVerticalBlock"][data-key="card_ergosign"]:hover {
        transform: translateY(-2px);
        background: linear-gradient(145deg, #0f172a, #1e293b, #164e63) padding-box,
                    linear-gradient(90deg, #3b82f6, #8b5cf6, #22d3ee, #14b8a6) border-box;
        box-shadow: 0 14px 34px rgba(56,189,248,0.25), 0 8px 20px rgba(0,0,0,0.25);
    }

    /* Headings and text inside cards */
    div[data-testid="stVerticalBlock"][data-key="card_scrape_all"] h3,
    div[data-testid="stVerticalBlock"][data-key="card_ergosign"] h3 {
        margin: 0 0 10px 0;
        color: #e5e7eb;
        font-size: 1.5rem;
        font-weight: 600;
        line-height: 1.4;
        text-align: center;
    }
    /* Paragraph and links inside cards */
    div[data-testid="stVerticalBlock"][data-key="card_scrape_all"] p,
    div[data-testid="stVerticalBlock"][data-key="card_ergosign"] p,
    div[data-testid="stVerticalBlock"][data-key="card_ergosign"] a {
        color: #cbd5e1;
        margin: 0 0 14px 0;
        font-size: 1.1rem;
        line-height: 1.5;
        text-align: center;
    }
    div[data-testid="stVerticalBlock"][data-key="card_ergosign"] a:hover {
        color: #e2e8f0;
        text-decoration: underline;
    }
    
    /* Ensure markdown paragraphs are center aligned */
    div[data-testid="stVerticalBlock"][data-key="card_scrape_all"] .stMarkdown,
    div[data-testid="stVerticalBlock"][data-key="card_ergosign"] .stMarkdown {
        text-align: center;
    }

    /* Button styling */
    div[data-testid="stVerticalBlock"][data-key="card_scrape_all"] .stButton>button,
    div[data-testid="stVerticalBlock"][data-key="card_ergosign"] .stButton>button {
        width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
# --------------------------------------------------------------------
# COMPETITOR ROW RENDERER
# --------------------------------------------------------------------

def render_competitor_controls(sites, group_name):
    """Render competitor cards and scrape buttons."""
    st.subheader(f"{group_name} Competitors List")

    st.markdown("""
        <style>
        /* Scrape button styling */
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
        
        /* Gradient separator line */
        .gradient-separator {
            height: 3px;
            background: linear-gradient(90deg, #1e3a8a, #312e81, #164e63, #0d9488);
            margin: 1rem 0;
            border-radius: 2px;
            opacity: 0.7;
            width: 85%;  /* Shortened to end before button */
        }
        
        /* Competitor name spacing */
        .competitor-name {
            padding: 0.75rem 0;
        }
        </style>
    """, unsafe_allow_html=True)

    # Create 3-column layout: Treemap | Competitor List | Buttons
    col_networkmap, col_list, col_buttons = st.columns([5, 1.5, 1.5], gap="medium")
    
    # with col_treemap:
    #     st.markdown("### 📊 Topic Distribution")
        
    #     try:
    #         # Get cached data
    #         df_cache = load_cache()
    #         if not df_cache.empty:
    #             # Import the treemap function from topic_visualization
    #             from topic_visualization import TopicVisualizer
                
    #             # Create visualizer instance
    #             visualizer = TopicVisualizer()
    #             visualizer.df = df_cache
    #             visualizer.competitor_data = df_cache
                
    #             # Add controls
    #             st.markdown("**Select Competitors:**")
    #             competitor_options = df_cache['website'].unique().tolist()
    #             selected_competitors = st.multiselect(
    #                 "Choose competitors:",
    #                 competitor_options,
    #                 default=competitor_options[:3] if len(competitor_options) > 3 else competitor_options,
    #                 key=f"sidebar_treemap_competitors_{group_name}"
    #             )
                
    #             st.markdown("**Top N Topics:**")
    #             top_n = st.slider("Number of topics:", 5, 20, 10, key=f"sidebar_treemap_top_n_{group_name}")
                
    #             if selected_competitors and len(selected_competitors) > 0:
    #                 # Filter data for selected competitors
    #                 filtered_df = df_cache[df_cache['website'].isin(selected_competitors)]
                    
    #                 if not filtered_df.empty:
    #                     # Prepare website topics data properly
    #                     website_topics = {}
    #                     for site in selected_competitors:
    #                         site_data = filtered_df[filtered_df['website'] == site]
    #                         topics_list = []
    #                         for topics_entry in site_data['topics'].dropna():
    #                             if isinstance(topics_entry, list):
    #                                 topics_list.extend([str(t).strip() for t in topics_entry if t and str(t).strip()])
    #                             elif isinstance(topics_entry, str) and topics_entry.strip() and topics_entry != '[]':
    #                                 try:
    #                                     import ast
    #                                     parsed = ast.literal_eval(topics_entry)
    #                                     if isinstance(parsed, list):
    #                                         topics_list.extend([str(t).strip() for t in parsed if t and str(t).strip()])
    #                                     else:
    #                                         topics_list.append(topics_entry.strip())
    #                                 except:
    #                                     topics_list.append(topics_entry.strip())
    #                         website_topics[site] = topics_list
                        
    #                     # Create a simple treemap without using the main visualization function
    #                     import plotly.express as px
    #                     import pandas as pd
                        
    #                     # Prepare data for simple treemap
    #                     all_topics = []
    #                     for site, topics in website_topics.items():
    #                         all_topics.extend(topics)
                        
    #                     if all_topics:
    #                         # Count topic frequencies
    #                         topic_counts = pd.Series(all_topics).value_counts().head(top_n)
                            
    #                         # Create simple treemap
    #                         fig = px.treemap(
    #                             values=topic_counts.values,
    #                             names=topic_counts.index,
    #                             title=f"Topic Distribution - {group_name}",
    #                             color_continuous_scale="Blues"
    #                         )
    #                         fig.update_layout(
    #                             height=400,
    #                             title_font_size=16,
    #                             font_size=12
    #                         )
    #                         st.plotly_chart(fig, width='stretch', height=400)
    #                     else:
    #                         st.info("No topics found for selected competitors")
    #                 else:
    #                     st.info("No data for selected competitors")
    #             else:
    #                 st.info("Please select at least one competitor")
    #         else:
    #             st.info("No data available - scrape some competitors first")
    #     except Exception as e:
    #         st.error(f"Treemap error: {str(e)}")
    #         st.info("Please check if data is properly loaded and try again")
    # Inside main.py (in the section where you display the Topic Relationship Map)
    with col_networkmap:
        st.markdown("### 🌐 Topic Relationship Map")

        try:
            df_cache = load_cache()
            if not df_cache.empty:
                competitor_group = "close" if group_name.lower() == "close" else "international"
                fig = create_topic_network(df_cache, competitor_group=competitor_group, max_topics=25)

                if fig:
                    st.plotly_chart(fig, use_container_width=True, key=f"network_chart_{group_name.lower()}")

                else:
                    st.info("No data found for this competitor group.")
            else:
                st.info("No data available — please scrape competitors first.")
        except Exception as e:
            st.error(f"Network map error: {e}")

    
    with col_list:
        st.markdown("### Competitors")
        for i, site in enumerate(sites):
            name = site.get("name") or site["url"].split("//")[-1].split("/")[0]
            url = site["url"]
            
            st.markdown(
                f"<div class='competitor-name'>"
                f"<a href='{url}' target='_blank' "
                f"style='color:#60a5fa; font-weight:600; "
                f"text-decoration:none; font-size:1.25rem;'>{name}</a>"
                f"</div>",
                unsafe_allow_html=True,
            )
            
            # Add gradient separator after each item (except the last one)
            if i < len(sites) - 1:
                st.markdown("<div class='gradient-separator'></div>", unsafe_allow_html=True)
    
    with col_buttons:
        st.markdown("### Actions")
        for i, site in enumerate(sites):
            name = site.get("name") or site["url"].split("//")[-1].split("/")[0]
            url = site["url"]
            
            # Add spacing to align with competitor names
            st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
            
            if st.button("Scrape", key=f"scrape_{group_name}_{i}"):
                with st.spinner(f"Scraping {name} ({url})..."):
                    updated_df = scrape_site_with_cache(url)
                    save_cache(updated_df)
                st.success(f"Done scraping {name}")
            
            # Add spacing after button to match competitor spacing
            if i < len(sites) - 1:
                st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

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

last_updated = "Unknown"

if not df_cache.empty and "last_scraped" in df_cache.columns:
    try:
        last_time = pd.to_datetime(df_cache["last_scraped"]).max()
        if pd.notna(last_time):
            now = datetime.now(timezone.utc)
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)

            delta = now - last_time
            total_minutes = int(delta.total_seconds() / 60)
            total_hours = total_minutes // 60

            if total_minutes < 60:
                last_updated = f"{total_minutes} min ago"
            elif total_hours < 24:
                last_updated = f"{total_hours} hr{'s' if total_hours != 1 else ''} ago"
            else:
                last_updated = last_time.strftime("%b %d, %Y")  # e.g. Oct 22, 2025
    except Exception as e:
        last_updated = "Unknown"


st.markdown("""
<div style="background: linear-gradient(90deg, #2563eb, #9333ea);
            padding: 1.5rem 2rem;
            border-radius: 12px;
            color: white;
            margin-bottom: 25px;
            text-align: center;">
    <h1 style="margin:0; font-size:2.5rem;">📊 Competitive Intelligence Dashboard</h1>
    <p style="margin:0.5rem 0 0; font-size:1.2rem;">
        Track, Analyze & Visualize competitor insights.
    </p>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------
# GLOBAL SEARCH (Inline input with clear icon inside)
# --------------------------------------------------------------------
# Add CSS for expander styling
st.markdown("""
    <style>
    /* Global Search Expander Styling */
    div[data-testid="stExpander"] details summary {
        font-size: 1.9rem !important;
        font-weight: 600 !important;
        padding: 1.3rem 1.5rem !important;
        color: #60a5fa !important;
        background: linear-gradient(135deg, #1e3a8a15, #312e8115) !important;
        border: 2px solid rgba(56,189,248,0.3) !important;
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stExpander"] details summary:hover {
        background: linear-gradient(135deg, #1e3a8a25, #312e8125) !important;
        border-color: rgba(56,189,248,0.5) !important;
        transform: translateY(-1px);
    }
    div[data-testid="stExpander"] details[open] summary {
        border-bottom-left-radius: 0 !important;
        border-bottom-right-radius: 0 !important;
        background: linear-gradient(135deg, #1e3a8a30, #312e8130) !important;
    }
    </style>
""", unsafe_allow_html=True)

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
            padding: 0.8rem 2.5rem 0.8rem 1rem;
            border-radius: 8px;
            border: 1px solid #374151;
            background-color: #1f2937;
            color: #f3f4f6;
            font-size: 1.1rem;
            outline: none;
        }
        .search-input::placeholder {
            color: #9ca3af;
            font-size: 1.05rem;
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
            padding: 0.8rem 1.5rem;
            font-weight: 600;
            font-size: 1.05rem;
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


# Assuming scrape_all_sites(), scrape_site_with_cache(), df_cache, SITES, and last_updated are defined.


# --------------------------------------------------------------------
# Scrape Section – Unified 3 Card Row (Blue–Purple–Teal Theme)
# --------------------------------------------------------------------
if not df_cache.empty and "last_scraped" in df_cache.columns:
    try:
        last_time = pd.to_datetime(df_cache["last_scraped"]).max()
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = now - last_time
        mins_ago = diff.total_seconds() / 60
        hours_ago = mins_ago / 60
        if mins_ago < 60:
            last_updated = f"{int(mins_ago)} mins ago"
        elif hours_ago < 24:
            last_updated = f"{int(hours_ago)} hrs ago"
        else:
            last_updated = last_time.strftime("%d %b %Y")
    except Exception:
        last_updated = "Recently"
else:
    last_updated = "Recently"

sites_scraped = len(df_cache["website"].unique()) if not df_cache.empty else len(SITES)

# --------------------------------------------------------------------
# 🎨 Styling – Teal / Blue / Purple Gradient Theme
# --------------------------------------------------------------------
st.markdown("""
<style>
.scrape-section {
    display: flex;
    flex-wrap: nowrap;
    justify-content: space-between;
    align-items: stretch;
    gap: 1.2rem;
    margin-bottom: 25px;
}

/* Gradient cards (Scrape All / Ergosign) */
.scrape-box {
    flex: 1 1 32%;
    background: linear-gradient(145deg, #1e3a8a, #312e81, #0d9488);
    border: 1px solid rgba(147,197,253,0.3);
    border-radius: 14px;
    padding: 1.5rem;
    box-shadow: 0 0 15px rgba(0,0,0,0.3);
    color: #f1f5f9;
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
    transition: all 0.3s ease;
    min-height: 230px;
}
.scrape-box:hover {
    transform: translateY(-3px);
    box-shadow: 0 0 25px rgba(56,189,248,0.4);
}

/* Metric card */
.metric-box {
    flex: 1 1 32%;
    background: linear-gradient(145deg, #0f172a, #1e293b, #164e63);
    border: 1px solid rgba(56,189,248,0.3);
    border-radius: 14px;
    padding: 1.5rem;
    color: #e5e7eb;
    text-align: center;
    box-shadow: 0 0 15px rgba(0,0,0,0.25);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    min-height: 180px;
    overflow: hidden;
}
.metric-box h2 {
    color: #7dd3fc;
    margin: 0.3rem 0;
    font-size: 2rem;
}
.metric-box small {
    color: #94a3b8;
    display: block;
    margin-bottom: 0.4rem;
}

/* Buttons inside cards */
.stButton>button {
    background: linear-gradient(90deg, #0ea5e9, #8b5cf6);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1.4rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    width: 80%;
}
.stButton>button:hover {
    background: linear-gradient(90deg, #06b6d4, #a855f7);
    transform: translateY(-2px);
}
.scrape-box h3 {
    color: #f9fafb;
    margin-bottom: 0.3rem;
}
.scrape-box p {
    color: #d1d5db;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------
# 🧩 Layout – Main Content (Left) + Two Vertical Cards (Right)
# --------------------------------------------------------------------
# Create main layout with left content and right sidebar
main_col, cards_col = st.columns([8, 2], gap="medium")

# Right column - Two vertical cards
with cards_col:
    # Add spacing to align cards with competitor list (after global search)
    st.markdown('<div style="margin-top: 8rem;"></div>', unsafe_allow_html=True)
    
    # --- Card 1: Scrape All Competitors ---
    container_scrape_all = st.container(border=True)
    with container_scrape_all:
        st.markdown("<h3 style='text-align: center;'>Web Scraping</h3>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 1.1rem; text-align: center;'>Fetch and update competitor insights from all tracked sites.</p>", unsafe_allow_html=True)
        # Center button using columns
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Scrape All Competitors", key="scrape_all_v3"):
                with st.spinner("Scraping all competitor websites..."):
                    scrape_all_sites()
                st.success("All competitors scraped successfully!")

    # --- Card 2: Scrape Ergosign ---
    container_ergosign = st.container(border=True)
    with container_ergosign:
        st.markdown("<h3 style='text-align: center;'>Ergosign Website</h3>", unsafe_allow_html=True)
        st.markdown('<p style="text-align: center;"><a href="https://www.ergosign.de/en/" target="_blank" style="color:#bfdbfe; font-size: 1.1rem;">ergosign.de/en</a></p>', unsafe_allow_html=True)
        # Center button using columns
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Scrape Ergosign", key="scrape_ergosign_v3"):
                with st.spinner("Scraping Ergosign website..."):
                    scrape_site_with_cache("https://www.ergosign.de/en/")


# Left column - Main content area
with main_col:
    # --------------------------------------------------------------------
    # SIDEBAR & MAIN CONTENT
    # --------------------------------------------------------------------
    # Enhanced sidebar styling with perfect alignment
    st.sidebar.markdown("""
        <style>
        /* Sidebar base */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        }
        [data-testid="stSidebar"] > div {
            padding: 1.5rem 1rem !important;
        }
        
        /* Headers - perfectly centered */
        [data-testid="stSidebar"] h2 {
            color: #60a5fa !important;
            font-weight: 600 !important;
            font-size: 1.8rem !important;
            text-align: center !important;
            margin: 1rem 0 1.5rem 0 !important;
            padding: 0 !important;
        }
        [data-testid="stSidebar"] h3 {
            color: #60a5fa !important;
            font-weight: 600 !important;
            font-size: 1.3rem !important;
            text-align: center !important;
            margin: 1.5rem 0 1rem 0 !important;
            padding: 0 !important;
            line-height: 1.4 !important;
        }
        
        /* Radio buttons section */
        [data-testid="stSidebar"] label[data-baseweb="radio"] {
            font-size: 1.1rem !important;
            color: #e2e8f0 !important;
            font-weight: 500 !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] {
            gap: 1rem !important;
            margin: 1rem 0 !important;
        }
        
        /* Metrics - centered with boxes */
        [data-testid="stSidebar"] [data-testid="stMetric"] {
            background: rgba(15, 23, 42, 0.6) !important;
            padding: 1.2rem 0.8rem !important;
            border-radius: 10px !important;
            margin: 0.8rem 0 !important;
            text-align: center !important;
        }
        [data-testid="stSidebar"] [data-testid="stMetricLabel"] {
            font-size: 1.05rem !important;
            color: #94a3b8 !important;
            text-align: center !important;
            width: 100% !important;
            display: block !important;
            margin-bottom: 0.6rem !important;
        }
        [data-testid="stSidebar"] [data-testid="stMetricLabel"] > div {
            justify-content: center !important;
            text-align: center !important;
        }
        [data-testid="stSidebar"] [data-testid="stMetricValue"] {
            font-size: 2.4rem !important;
            color: #60a5fa !important;
            font-weight: 700 !important;
            text-align: center !important;
            width: 100% !important;
            display: block !important;
        }
        [data-testid="stSidebar"] [data-testid="stMetricValue"] > div {
            justify-content: center !important;
            text-align: center !important;
        }
        
        /* Info boxes */
        [data-testid="stSidebar"] .stAlert {
            text-align: center !important;
            font-size: 1.15rem !important;
            padding: 0.8rem 1rem !important;
            margin: 1rem 0 !important;
        }
        
        /* Dividers */
        [data-testid="stSidebar"] hr {
            margin: 2rem 0 !important;
            border: none !important;
            border-top: 2px solid rgba(96, 165, 250, 0.25) !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown('<h2 style="text-align: center; margin: 1.5rem 0;">Competitor View</h2>', unsafe_allow_html=True)
    
    view_option = st.sidebar.radio(
        "Select Competitor Group:",
        ("Close Competitors", "International Competitors"),
        help="Choose which competitor group to analyze"
    )
    
    st.sidebar.markdown("---")
    
    # Add Topic Analysis Stats
    if not df_cache.empty:
        if view_option == "Close Competitors":
            st.sidebar.markdown('<h3 style="text-align: center;">Topic Analysis – Close Competitors</h3>', unsafe_allow_html=True)
        else:
            st.sidebar.markdown('<h3 style="text-align: center;">Topic Analysis – International Competitors</h3>', unsafe_allow_html=True)
        
        # Calculate total websites scraped
        total_websites = len(df_cache['website'].unique())
        st.sidebar.metric("Total Websites Scrapped", total_websites)
        
        # Calculate total pages scraped
        st.sidebar.metric("Total Pages Scrapped", len(df_cache))
        
        # Calculate unique topics (properly handling list and string types)
        all_topics = []
        for topics_entry in df_cache['topics'].dropna():
            if isinstance(topics_entry, list):
                # Handle list type
                all_topics.extend([str(t).strip() for t in topics_entry if t and str(t).strip()])
            elif isinstance(topics_entry, str) and topics_entry.strip() and topics_entry != '[]':
                # Handle string type - try to parse as list first
                try:
                    import ast
                    parsed = ast.literal_eval(topics_entry)
                    if isinstance(parsed, list):
                        all_topics.extend([str(t).strip() for t in parsed if t and str(t).strip()])
                    else:
                        all_topics.extend([t.strip() for t in topics_entry.split(',') if t.strip()])
                except:
                    # Fallback to split by comma
                    all_topics.extend([t.strip() for t in topics_entry.split(',') if t.strip()])
        
        # Remove empty strings and get unique topics
        all_topics = [t for t in all_topics if t]
        unique_topics = len(set(all_topics))
        
        # Last update info
        st.sidebar.markdown("---")
        st.sidebar.markdown('<h3 style="text-align: center;">Last Update</h3>', unsafe_allow_html=True)
        st.sidebar.info(f"{last_updated}")
    
    st.sidebar.markdown("---")

    if view_option == "Close Competitors":
        close_sites = [s for s in SITES if s["type"] == "competitor_close"]
        if close_sites:
            render_competitor_controls(close_sites, "Close")
            # Add spacing before tabs
            st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
        df = load_cache()
        if not df.empty:
            show_topic_visualization(df, competitor_type="close", mode=mode)
        else:
            st.info("No data available yet. Run scraper first.")
    else:
        intl_sites = [s for s in SITES if s["type"] == "competitor_international"]
        if intl_sites:
            render_competitor_controls(intl_sites, "International")
            # Add spacing before tabs
            st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
        df = load_cache()
        if not df.empty:
            show_topic_visualization(df, competitor_type="international", mode=mode)
        else:
            st.info("No data available yet. Run scraper first.")
