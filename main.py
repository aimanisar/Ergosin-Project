# main.py
import os
import streamlit as st
import pandas as pd
from urllib.parse import urlparse
from scrape import scrape_website, extract_main_content, extract_internal_links
from llm_process import call_llm_batch, filter_links_with_llm
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from datetime import datetime


# --- minimal styling ---
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

# --------------------------- Config ---------------------------
SITES = [
    {"type": "base", "url": "https://ergosign.de/"},
    {"type": "competitor", "url": "https://www.cobeisfresh.com/"},
    {"type": "competitor", "url": "https://www.designaffairs.com/"},
    {"type": "competitor", "url": "https://www.designit.com/"},
    {"type": "competitor", "url": "https://www.diva-e.com/de/"},
    {"type": "competitor", "url": "https://www.frogdesign.com/"},
    {"type": "competitor", "url": "https://www.futurice.com/"},
    {"type": "competitor", "url": "https://ginetta.net/"},
    {"type": "competitor", "url": "https://www.ideo.com/eu"},
    {"type": "competitor", "url": "https://www.phoenixdesign.com/"},
    {"type": "competitor", "url": "https://www.centigrade.de/de/"},
    {"type": "competitor", "url": "https://www.shapefield.de/shape/welcome"},
    {"type": "competitor", "url": "https://www.uid.com/de/"},
    {"type": "competitor", "url": "https://www.consulteer.com/"},
    {"type": "competitor", "url": "https://www.404.agency/hr/"},
    {"type": "competitor", "url": "https://www.custom-interactions.com/"},
]

# SKIP_PATH = "unique_urls.csv"
# try:
#     skip_df = pd.read_csv(SKIP_PATH)
#     SKIP_URLS = set(u.strip().rstrip("/") for u in skip_df["url"].dropna())
# except Exception:
#     SKIP_URLS = set()

# def should_skip(url: str) -> bool:
#     return url.strip().rstrip("/") in SKIP_URLS

# BLOCKED_BASES = [
#     "/career", "/careers", "/about", "/cookies", "/subscribe", "/privacy", "/work", "/studios", "/report-an-incident",
#     "/karriere", "/jobs", "/ueber-uns", "/unternehmen", "/team", "/contact"
# ]

CSV_PATH = "scraped_data.csv"

if "cancel_scrape" not in st.session_state:
    st.session_state["cancel_scrape"] = False

# --------------------------- Helpers --------------------------
# def is_blocked(url: str) -> bool:
#     p = urlparse(url).path.lower().rstrip("/")
#     for base in BLOCKED_BASES:
#         b = base.rstrip("/").lower()
#         if p == b or p.startswith(b + "/"):
#             return True
#     return False

# def _merge_to_csv(path: str, new_df: pd.DataFrame, subset_cols: list[str]):
#     if new_df is None or new_df.empty:
#         return
#     if os.path.exists(path):
#         old = pd.read_csv(path)
#         cat = pd.concat([old, new_df], ignore_index=True)
#         cat = cat.drop_duplicates(subset=subset_cols, keep="last")
#     else:
#         cat = new_df
#     cat.to_csv(path, index=False, encoding="utf-8")

def make_hash(text: str) -> str:
    """Generate MD5 hash of text for change detection."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()

# ------------------------- Scrape Logic -----------------------
# def scrape_site(site_url: str):
#     """Scrape only this site (main page + LLM-filtered internal links)."""
#     domain = urlparse(site_url).netloc
#     rows = []

#     status = st.empty()
#     url_log = st.container()
#     prog = st.progress(0, text=f"Starting: {site_url}")

#     def _log(msg: str):
#         status.write(msg)
#         with url_log:
#             st.write(msg)

#     if should_skip(site_url):
#         st.info(f"⏭️ Skipped (in skip list): {site_url}")
#         return pd.DataFrame(columns=["website","page_url","page_name","content","topics"])

#     _log(f"🔎 Scraping main page: {site_url}")
#     main_html  = scrape_website(site_url)
#     main_clean = extract_main_content(main_html)
#     rows.append({
#         "website": domain, "page_url": site_url, "page_name": "home",
#         "content": main_clean, "topics": ""
#     })

#     # --- Extract + LLM filter subpages ---
#     subpages = extract_internal_links(main_html, site_url)

#     seen = set()
#     subpages = [u for u in subpages if not (u in seen or seen.add(u))]

#     subpages = filter_links_with_llm(subpages, site_url)  # 🔹 NEW: LLM filtering

#     total = max(1, len(subpages) + 1)
#     done = 1
#     prog.progress(done/total, text=f"{domain}: {done}/{total}")

#     for sub_url in subpages:
#         if should_skip(sub_url):
#             _log(f"⏭️ Skipped (in skip list): {sub_url}")
#             done += 1
#             prog.progress(min(done/total, 1.0), text=f"{domain}: {done}/{total}")
#             continue

#         try:
#             _log(f"🔎 Scraping subpage: {sub_url}")
#             sub_html  = scrape_website(sub_url)
#             sub_clean = extract_main_content(sub_html)
#             sub_name  = urlparse(sub_url).path.strip("/") or "home"
#             rows.append({
#                 "website": domain, "page_url": sub_url, "page_name": sub_name,
#                 "content": sub_clean, "topics": ""
#             })
#         except Exception as e:
#             _log(f"⚠️ Error scraping {sub_url}: {e}")

#         done += 1
#         prog.progress(min(done/total, 1.0), text=f"{domain}: {done}/{total}")

#     prog.empty(); status.empty()
#     return pd.DataFrame(rows, columns=["website","page_url","page_name","content","topics"])

from datetime import datetime

def scrape_site(site_url: str):
    """Scrape only this site (main page + LLM-filtered internal links)."""
    domain = urlparse(site_url).netloc
    rows = []

    status = st.empty()
    url_log = st.container()
    prog = st.progress(0, text=f"Starting: {site_url}")

    def _log(msg: str):
        status.write(msg)
        with url_log:
            st.write(msg)

    now = datetime.utcnow().isoformat()

    # --- Main page ---
    _log(f"🔎 Scraping main page: {site_url}")
    main_html  = scrape_website(site_url)
    main_clean = extract_main_content(main_html)
    rows.append({
        "website": domain, "page_url": site_url, "page_name": "home",
        "content": main_clean, "content_hash": make_hash(main_clean),
        "topics": "", "last_scraped": now
    })

    # --- Extract + LLM filter subpages ---
    subpages = extract_internal_links(main_html, site_url)
    seen = set()
    subpages = [u for u in subpages if not (u in seen or seen.add(u))]
    subpages = filter_links_with_llm(subpages, site_url)  # 🔹 LLM decides

    total = max(1, len(subpages) + 1)
    done = 1
    prog.progress(done/total, text=f"{domain}: {done}/{total}")

    for sub_url in subpages:
        try:
            _log(f"🔎 Scraping subpage: {sub_url}")
            sub_html  = scrape_website(sub_url)
            sub_clean = extract_main_content(sub_html)
            sub_name  = urlparse(sub_url).path.strip("/") or "home"
            rows.append({
                "website": domain, "page_url": sub_url, "page_name": sub_name,
                "content": sub_clean, "content_hash": make_hash(sub_clean),
                "topics": "", "last_scraped": now
            })
        except Exception as e:
            _log(f"⚠️ Error scraping {sub_url}: {e}")

        done += 1
        prog.progress(min(done/total, 1.0), text=f"{domain}: {done}/{total}")

    prog.empty(); status.empty()
    return pd.DataFrame(rows, columns=["website","page_url","page_name","content","content_hash","topics","last_scraped"])


def scrape_all_sites(max_workers: int = 2):
    """Scrape ALL SITES in parallel, detect changes by hash, and save one CSV."""
    total_sites = len(SITES)
    total_rows = 0
    processed_sites = 0

    # Load existing cache if file exists
    if os.path.exists(CSV_PATH):
        cached_df = pd.read_csv(CSV_PATH)
    else:
        cached_df = pd.DataFrame(columns=["website","page_url","page_name","content","topics","content_hash"])

    overall = st.progress(0, text="Starting full run…")

    # Parallel execution
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scrape_site, site["url"].strip()): site for site in SITES}

        for future in as_completed(futures):
            site = futures[future]
            site_url = site["url"].strip()

            if st.session_state.get("cancel_scrape"):
                st.warning("⛔ Full run terminated by user. Stopping now.")
                break

            try:
                raw_df = future.result()
            except Exception as e:
                st.error(f"⚠️ Error scraping {site_url}: {e}")
                continue

            # Merge new scrape with cache
            merged_df = pd.concat([cached_df, raw_df], ignore_index=True)

            # Always keep the last version of each page
            merged_df = merged_df.drop_duplicates(subset=["page_url"], keep="last")

            # 🔹 Detect pages needing updates (new, empty topics, or content changed)
            to_update = merged_df[
                (merged_df["topics"].isna()) |
                (merged_df["topics"] == "") |
                (merged_df["content_hash"] != merged_df.groupby("page_url")["content_hash"].transform("last"))
            ]

            pages_to_process = list(zip(to_update["page_url"], to_update["content"]))

            skipped_count = len(merged_df) - len(to_update)
            new_count = len(pages_to_process)

            if new_count > 0:
                st.info(f"🔎 {site_url}: {skipped_count} unchanged, processing {new_count} new/updated pages with LLM...")
                topics_result = call_llm_batch(pages_to_process)
                topics_map = {r["url"]: r.get("topics", []) for r in topics_result}

                merged_df.loc[merged_df["page_url"].isin(topics_map.keys()), "topics"] = \
                    merged_df["page_url"].map(lambda u: ", ".join(topics_map.get(u, [])))
            else:
                st.success(f"✅ {site_url}: all {skipped_count} pages unchanged, no LLM calls needed.")

            # Save updated cache
            cached_df = merged_df
            cached_df.to_csv(CSV_PATH, index=False, encoding="utf-8")

            total_rows += len(raw_df)
            processed_sites += 1
            overall.progress(processed_sites / total_sites, text=f"Processed {processed_sites}/{total_sites} sites")

    overall.empty()
    st.session_state["cancel_scrape"] = False
    st.success(f"✅ Full run complete. Added/updated {total_rows} rows across {processed_sites} sites.")



# ---------------------------- UI ------------------------------
st.title("Automated Website Scraper (Raw + Topics)")

with st.container():
    c1, c2 = st.columns([6,6], gap="small")
    with c1:
        if st.button("❌ Terminate", use_container_width=True):
            st.session_state["cancel_scrape"] = True
            st.warning("Termination requested. Will stop after the current page.")
    with c2:
        if st.button("🚀 Scrape ALL Websites", type="primary", use_container_width=True):
            scrape_all_sites()

st.caption("Terminate stops after the current page. Scrape ALL runs sites in order.")

# ------------------------ CSV Status & Downloads ------------------------
with st.expander("CSV status & downloads", expanded=False):
    if os.path.exists(CSV_PATH):
        _df = pd.read_csv(CSV_PATH)
        st.write(f"**Data** — {_df.shape[0]} rows")
        st.download_button("⬇️ Download CSV", _df.to_csv(index=False).encode("utf-8"),
                           file_name=CSV_PATH, mime="text/csv", key="dl_data")
    else:
        st.info("No CSV yet.")
