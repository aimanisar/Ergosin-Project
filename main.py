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
    {"type": "competitor", "url": "https://www.wikipedia.org/"}
]

CSV_PATH = "scraped_data.csv"

if "cancel_scrape" not in st.session_state:
    st.session_state["cancel_scrape"] = False


# --------------------------- Helpers --------------------------
def make_hash(text: str) -> str:
    """Generate MD5 hash of text for change detection."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ------------------------- Scrape Logic -----------------------
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
    main_html = scrape_website(site_url)
    main_clean = extract_main_content(main_html)
    main_clean = main_clean.replace("\n", " ").replace("\r", " ").strip()
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
    prog.progress(done / total, text=f"{domain}: {done}/{total}")

    for sub_url in subpages:
        try:
            _log(f"🔎 Scraping subpage: {sub_url}")
            sub_html = scrape_website(sub_url)
            sub_clean = extract_main_content(sub_html)
            sub_clean = sub_clean.replace("\n", " ").replace("\r", " ").strip()
            sub_name = urlparse(sub_url).path.strip("/") or "home"
            rows.append({
                "website": domain, "page_url": sub_url, "page_name": sub_name,
                "content": sub_clean, "content_hash": make_hash(sub_clean),
                "topics": "", "last_scraped": now
            })
        except Exception as e:
            _log(f"⚠️ Error scraping {sub_url}: {e}")

        done += 1
        prog.progress(min(done / total, 1.0), text=f"{domain}: {done}/{total}")

    prog.empty()
    status.empty()
    return pd.DataFrame(rows, columns=[
        "website", "page_url", "page_name", "content", "content_hash", "topics", "last_scraped"
    ])


def scrape_all_sites(max_workers: int = 2):
    """Scrape ALL SITES in parallel, detect changes by hash, and save one CSV."""
    total_sites = len(SITES)
    total_rows = 0
    processed_sites = 0

    if os.path.exists(CSV_PATH):
        cached_df = pd.read_csv(CSV_PATH)
    else:
        cached_df = pd.DataFrame(columns=[
            "website", "page_url", "page_name", "content", "topics", "content_hash", "last_scraped"
        ])

    overall = st.progress(0, text="Starting full run…")

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

            merged_df = pd.concat([cached_df, raw_df], ignore_index=True)
            merged_df = merged_df.drop_duplicates(subset=["page_url"], keep="last")

            # Detect new/changed pages
            to_update = merged_df[
                (merged_df["topics"].isna()) |
                (merged_df["topics"] == "") |
                (merged_df["content_hash"] != merged_df.groupby("page_url")["content_hash"].transform("last"))
            ]

            pages_to_process = [
                {"url": row["page_url"], "content": row["content"]}
                for _, row in to_update.iterrows()
            ]

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

            cached_df = merged_df
            cached_df.to_csv(CSV_PATH, index=False, encoding="utf-8")
            st.write(f"💾 Saved {len(cached_df)} rows to {CSV_PATH}")

            total_rows += len(raw_df)
            processed_sites += 1
            overall.progress(processed_sites / total_sites, text=f"Processed {processed_sites}/{total_sites} sites")

    overall.empty()
    st.session_state["cancel_scrape"] = False
    st.success(f"✅ Full run complete. Added/updated {total_rows} rows across {processed_sites} sites.")


# ---------------------------- UI ------------------------------
st.title("Automated Website Scraper (Raw + Topics)")

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

# ------------------------ CSV Status & Downloads ------------------------
with st.expander("CSV status & downloads", expanded=False):
    if os.path.exists(CSV_PATH):
        _df = pd.read_csv(CSV_PATH)
        st.write(f"**Data** — {_df.shape[0]} rows, columns: {_df.columns.tolist()}")
        st.download_button("⬇️ Download CSV", _df.to_csv(index=False).encode("utf-8"),
                           file_name=CSV_PATH, mime="text/csv", key="dl_data")
    else:
        st.info("No CSV yet.")


# ------------------------ Per-Site Scrape Controls ------------------------
st.subheader("Scrape Individual Websites")

for i, site in enumerate(SITES):
    site_url = site["url"].strip()
    site_type = site["type"]

    with st.container():
        st.markdown('<div class="site-card">', unsafe_allow_html=True)
        r1c1, r1c2, r1c3, r1c4 = st.columns([6, 2, 2, 2], gap="medium")

        with r1c1:
            st.markdown(f"**[{site_url}]({site_url})**")
            st.markdown(f'<span class="badge {site_type}">{site_type}</span>', unsafe_allow_html=True)

        with r1c2:
            if st.button("Scrape", key=f"scrape_{i}"):
                with st.spinner(f"Scraping {site_url}…"):
                    raw_df = scrape_site(site_url)

                    if os.path.exists(CSV_PATH):
                        cached_df = pd.read_csv(CSV_PATH)
                    else:
                        cached_df = pd.DataFrame(columns=[
                            "website", "page_url", "page_name", "content", "content_hash", "topics", "last_scraped"
                        ])

                    merged_df = pd.concat([cached_df, raw_df], ignore_index=True)
                    merged_df = merged_df.drop_duplicates(subset=["page_url"], keep="last")

                    to_update = merged_df[
                        (merged_df["topics"].isna()) |
                        (merged_df["topics"] == "") |
                        (merged_df["content_hash"] != merged_df.groupby("page_url")["content_hash"].transform("last"))
                    ]

                    pages_to_process = [
                        {"url": row["page_url"], "content": row["content"]}
                        for _, row in to_update.iterrows()
                    ]

                    if len(pages_to_process) > 0:
                        st.info(f"🔎 {len(pages_to_process)} new/updated pages need topics...")
                        topics_result = call_llm_batch(pages_to_process)
                        topics_map = {r["url"]: r.get("topics", []) for r in topics_result}
                        merged_df.loc[merged_df["page_url"].isin(topics_map.keys()), "topics"] = \
                            merged_df["page_url"].map(lambda u: ", ".join(topics_map.get(u, [])))
                    else:
                        st.success("✅ No new/updated pages, nothing sent to LLM.")

                    merged_df.to_csv(CSV_PATH, index=False, encoding="utf-8")
                    st.write(f"💾 Saved {len(merged_df)} rows to {CSV_PATH}")

                st.success(f"✅ Done scraping {site_url} ({len(raw_df)} pages scraped)")

        with r1c3:
            if st.button("Terminate", key=f"term_{i}"):
                st.session_state["cancel_scrape"] = True
                st.warning("Termination requested for this site. Will stop after current page.")

        with r1c4:
            st.markdown(f'<a href="{site_url}" target="_blank">Open</a>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
