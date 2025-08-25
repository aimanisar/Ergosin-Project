# main.py
import os
import streamlit as st
import pandas as pd
from urllib.parse import urlparse
from scrape import scrape_website, extract_main_content, extract_internal_links
from llm_process import call_llm

# --- minimal styling ---
st.markdown("""
<style>
/* page width + nicer typography spacing */
.block-container { max-width: 1100px !important; }

/* toolbar buttons */
.toolbar .stButton>button { height: 48px; font-weight: 600; }

/* site cards */
.site-card {
  border: 1px solid #eaeaea; border-radius: 14px; padding: 14px 16px;
  margin-bottom: 12px; background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}

/* type badge */
.badge {
  display: inline-block; padding: 3px 8px; border-radius: 999px;
  font-size: 12px; font-weight: 600; letter-spacing: .2px;
  background: #eef2ff; color: #3b5bdb;  /* indigo */
}
.badge.base { background:#e6fcf5; color:#087f5b; }      /* teal */
.badge.competitor { background:#fff1f0; color:#d64545; }/* red */

/* equal width buttons in action row */
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

# Load URLs to skip (from your CSV/Excel)
SKIP_PATH = "unique_urls.csv"        # or "unique_urls.xlsx"
try:
    skip_df = pd.read_csv(SKIP_PATH)  # if Excel: pd.read_excel(SKIP_PATH)
    SKIP_URLS = set(u.strip().rstrip("/") for u in skip_df["url"].dropna())
except Exception:
    SKIP_URLS = set()

def should_skip(url: str) -> bool:
    return url.strip().rstrip("/") in SKIP_URLS

# Block Careers/About and localized variants (and subpaths)
BLOCKED_BASES = [
    "/career", "/careers", "/about",
    "/karriere", "/jobs", "/ueber-uns", "/unternehmen", "/team"
]

RAW_CSV = "scraped_data_raw.csv"
DIGEST_CSV = "scraped_data_digest.csv"

# ------------------------- Session State ----------------------

if "cancel_scrape" not in st.session_state:
    st.session_state["cancel_scrape"] = False

# --------------------------- Helpers -------------------------

def is_blocked(url: str) -> bool:
    """True if URL path is one of the blocked bases or any subpath."""
    p = urlparse(url).path.lower().rstrip("/")
    for base in BLOCKED_BASES:
        b = base.rstrip("/").lower()
        if p == b or p.startswith(b + "/"):
            return True
    return False

def _merge_to_csv(path: str, new_df: pd.DataFrame, subset_cols: list[str]):
    """Merge new_df into CSV at path, de-duplicating on subset_cols (new rows win)."""
    if new_df is None or new_df.empty:
        return
    if os.path.exists(path):
        old = pd.read_csv(path)
        cat = pd.concat([old, new_df], ignore_index=True)
        cat = cat.drop_duplicates(subset=subset_cols, keep="last")
    else:
        cat = new_df
    cat.to_csv(path, index=False, encoding="utf-8")

# ------------------------- Scrape Logic -----------------------

def scrape_site(site_url: str):
    """
    Scrape only this site (main page + allowed internal links) and return (raw_df, dig_df).
    Shows a progress bar and live URL updates. Honors st.session_state['cancel_scrape'].
    """
    domain = urlparse(site_url).netloc
    raw_rows, digest_rows = [], []

    # --- UI placeholders for live feedback ---
    status = st.empty()          # line of text with current action
    url_log = st.container()     # scrolling log of URLs being scraped
    prog = st.progress(0, text=f"Starting: {site_url}")

    def _log(msg: str):
        status.write(msg)
        with url_log:
            st.write(msg)

    # ----- MAIN PAGE -----
    if not is_blocked(site_url):

        if should_skip(site_url):
            st.info(f"⏭️ Skipped (in skip list): {site_url}")
            return (pd.DataFrame(columns=["website","page_url","page_name","content"]),
                    pd.DataFrame(columns=["website","page_url","title","summary","topics"]))

        if st.session_state.get("cancel_scrape"):
            st.warning("⛔ Terminated before starting main page.")
            prog.empty(); status.empty()
            return (pd.DataFrame(columns=["website","page_url","page_name","content"]),
                    pd.DataFrame(columns=["website","page_url","title","summary","topics"]))

        _log(f"🔎 Scraping main page: {site_url}")
        main_html  = scrape_website(site_url)
        main_clean = extract_main_content(main_html)

        raw_rows.append({
            "website": domain, "page_url": site_url, "page_name": "home", "content": main_clean
        })

        if st.session_state.get("cancel_scrape"):
            st.warning("⛔ Terminated after main page.")
            prog.empty(); status.empty()
            raw_df = pd.DataFrame(raw_rows, columns=["website","page_url","page_name","content"])
            dig_df = pd.DataFrame(columns=["website","page_url","title","summary","topics"])
            st.session_state["cancel_scrape"] = False
            return raw_df, dig_df

        _log("🧠 Summarizing main page with LLM…")
        main_info = call_llm(main_clean)
        digest_rows.append({
            "website": domain, "page_url": site_url,
            "title":  main_info.get("title", "Untitled"),
            "summary": main_info.get("summary", ""),
            "topics": ", ".join(main_info.get("topics", []))
        })

        # ----- SUBPAGES -----
        subpages = extract_internal_links(main_html, site_url)
        seen = set()
        subpages = [u for u in subpages if not (u in seen or seen.add(u))]

        total = max(1, len(subpages) + 1)  # +1 for main page
        done = 1
        prog.progress(done/total, text=f"{domain}: {done}/{total}")

        for sub_url in subpages:
            if st.session_state.get("cancel_scrape"):
                st.warning("⛔ Terminated by user (will stop now).")
                break

            if is_blocked(sub_url) or should_skip(sub_url):
                _log(f"⏭️ Skipped blocked: {sub_url}")
                done += 1
                prog.progress(min(done/total, 1.0), text=f"{domain}: {done}/{total}")
                continue

            try:
                _log(f"🔎 Scraping subpage: {sub_url}")
                sub_html  = scrape_website(sub_url)
                sub_clean = extract_main_content(sub_html)
                sub_name  = urlparse(sub_url).path.strip("/") or "home"

                raw_rows.append({
                    "website": domain, "page_url": sub_url, "page_name": sub_name, "content": sub_clean
                })

                if st.session_state.get("cancel_scrape"):
                    _log("⛔ Terminated after fetching subpage content.")
                    break

                _log("🧠 Summarizing with LLM…")
                sub_info = call_llm(sub_clean)
                digest_rows.append({
                    "website": domain, "page_url": sub_url,
                    "title":  sub_info.get("title", "Untitled"),
                    "summary": sub_info.get("summary", ""),
                    "topics": ", ".join(sub_info.get("topics", []))
                })
            except Exception as e:
                _log(f"⚠️ Error scraping {sub_url}: {e}")

            done += 1
            prog.progress(min(done/total, 1.0), text=f"{domain}: {done}/{total}")
    else:
        st.info(f"Skipped blocked main URL: {site_url}")

    # cleanup
    prog.empty(); status.empty()
    st.session_state["cancel_scrape"] = False

    raw_df = pd.DataFrame(raw_rows, columns=["website", "page_url", "page_name", "content"])
    dig_df = pd.DataFrame(digest_rows, columns=["website", "page_url", "title", "summary", "topics"])
    return raw_df, dig_df

def scrape_all_sites():
    """Scrape ALL SITES in order, honoring Terminate, and merge into CSVs as we go."""
    overall = st.progress(0, text="Starting full run…")
    total_sites = len(SITES)
    total_raw, total_dig = 0, 0

    for idx, site in enumerate(SITES, start=1):
        if st.session_state.get("cancel_scrape"):
            st.warning("⛔ Full run terminated by user. Stopping now.")
            break

        site_url = site["url"].strip()
        with st.spinner(f"Scraping {site_url} ..."):
            raw_df, dig_df = scrape_site(site_url)
            _merge_to_csv(RAW_CSV, raw_df, subset_cols=["page_url"])
            _merge_to_csv(DIGEST_CSV, dig_df, subset_cols=["page_url"])
            total_raw += len(raw_df)
            total_dig += len(dig_df)

        overall.progress(min(idx/total_sites, 1.0), text=f"Processed {idx}/{total_sites} sites")

    overall.empty()
    st.session_state["cancel_scrape"] = False  # reset for next run
    st.success(f"✅ Full run complete. Added/updated {total_raw} raw rows and {total_dig} digest rows across {idx if idx<=total_sites else total_sites} sites.")

# ---------------------------- UI ------------------------------

st.title("Automated Website Scraper")

with st.container():
    c1, c2 = st.columns([6,6], gap="small")
    with c1:
        st.markdown('<div class="toolbar">', unsafe_allow_html=True)
        if st.button("❌ Terminate", use_container_width=True):
            st.session_state["cancel_scrape"] = True
            st.warning("Termination requested. Will stop after the current page.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="toolbar">', unsafe_allow_html=True)
        if st.button("🚀 Scrape ALL Websites", type="primary", use_container_width=True):
            scrape_all_sites()
        st.markdown('</div>', unsafe_allow_html=True)

st.caption("Terminate stops after the current page. Scrape ALL runs sites in order.")
st.caption("Click **Scrape** next to any site to process only that site. Results are merged into CSVs.")


# Per-site list
for i, site in enumerate(SITES):
    site_url = site["url"].strip()
    site_type = site["type"]

    with st.container():
        st.markdown('<div class="site-card">', unsafe_allow_html=True)
        r1c1, r1c2, r1c3, r1c4 = st.columns([6,2,2,2], gap="medium")

        # Left: URL + type badge
        with r1c1:
            st.markdown(f"**[{site_url}]({site_url})**")
            st.markdown(f'<span class="badge {site_type}">{site_type}</span>', unsafe_allow_html=True)

        # Actions
        with r1c2:
            st.markdown('<div class="action-col">', unsafe_allow_html=True)
            if st.button("Scrape", key=f"scrape_{i}"):
                with st.status(f"Scraping {site_url}…", state="running") as s:
                    raw_df, dig_df = scrape_site(site_url)
                    _merge_to_csv(RAW_CSV, raw_df, subset_cols=["page_url"])
                    _merge_to_csv(DIGEST_CSV, dig_df, subset_cols=["page_url"])
                    s.update(label=f"Done {site_url}", state="complete")
                st.success(f"✅ {len(raw_df)} raw rows, {len(dig_df)} digest rows")
                if not dig_df.empty:
                    st.dataframe(dig_df.head(12), use_container_width=True, height=240)
            st.markdown('</div>', unsafe_allow_html=True)

        with r1c3:
            st.markdown('<div class="action-col">', unsafe_allow_html=True)
            if st.button("Terminate", key=f"term_{i}"):
                st.session_state["cancel_scrape"] = True
                st.warning("Termination requested for this site. Will stop after the current page.")
            st.markdown('</div>', unsafe_allow_html=True)

        with r1c4:
            st.markdown('<div class="action-col">', unsafe_allow_html=True)
            st.markdown(
                f'<a class="btn btn-open" href="{site_url}" target="_blank">Open</a>',
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)


# ------------------------ CSV Status & Downloads ------------------------

with st.expander("CSV status & downloads", expanded=False):
    # RAW
    if os.path.exists(RAW_CSV):
        _raw_df = pd.read_csv(RAW_CSV)
        st.write(f"**Raw Data** — {_raw_df.shape[0]} rows")
        st.download_button("⬇️ Download Raw CSV", _raw_df.to_csv(index=False).encode("utf-8"),
                           file_name=RAW_CSV, mime="text/csv", key="dl_raw")
    else:
        st.info("No raw CSV yet.")

    # DIGEST
    if os.path.exists(DIGEST_CSV):
        _dig_df = pd.read_csv(DIGEST_CSV)
        st.write(f"**Summarised Data** — {_dig_df.shape[0]} rows")
        st.download_button("⬇️ Download Summarised CSV", _dig_df.to_csv(index=False).encode("utf-8"),
                           file_name=DIGEST_CSV, mime="text/csv", key="dl_digest")
    else:
        st.info("No digest CSV yet.")

