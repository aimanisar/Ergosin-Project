# workflow.py
"""
High-level workflow logic for scraping websites and updating topics.
Uses scrape.py, llm_process.py, and storage.py.
"""

import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import SITES
from scrape import scrape_site
from llm_process import call_llm_batch
from storage import load_cache, save_cache, merge_with_cache
import pandas as pd



def update_topics(df):
    to_update = df[(df["topics"].isna()) | (df["topics"] == "") |
                   (df["summary"].isna()) | (df["summary"] == "")]
    pages_to_process = [
        {"url": row["page_url"], "content": row["content"]}
        for _, row in to_update.iterrows()
    ]

    if len(pages_to_process) > 0:
        st.info(f"🔎 {len(pages_to_process)} pages need topics+summary... sending to LLM")
        results = call_llm_batch(pages_to_process)
        lookup = {r["url"]: r for r in results}

        for idx, row in df.iterrows():
            url = row["page_url"]
            if url in lookup:
                df.at[idx, "summary"] = lookup[url].get("summary", "")
                df.at[idx, "topics"] = ", ".join(lookup[url].get("topics", []))
    else:
        st.success("✅ All pages already have summary & topics.")
    return df

def enrich_with_llm(raw_df: pd.DataFrame, merged_df: pd.DataFrame, site_url: str = "", batch_size: int = 5) -> pd.DataFrame:
    to_update = raw_df[
        (raw_df["topics"].isna()) | (raw_df["topics"] == "") |
        (raw_df["summary"].isna()) | (raw_df["summary"] == "")
    ]

    pages_to_process = [
        {"url": row["page_url"], "content": row["content"]}
        for _, row in to_update.iterrows()
    ]

    if not pages_to_process:
        st.success(f"✅ {site_url or 'This site'}: no new/updated pages, skipping LLM.")
        return merged_df

    st.info(f"🔎 {len(pages_to_process)} new/updated pages {f'for {site_url}' if site_url else ''} → sending to LLM...")

    # 🔹 process in batches
    lookup = {}
    for i in range(0, len(pages_to_process), batch_size):
        batch = pages_to_process[i:i+batch_size]
        results = call_llm_batch(batch)
        for r in results:
            lookup[r["url"]] = r

    # apply results back to df
    for idx, row in merged_df.iterrows():
        url = row["page_url"]
        if url in lookup:
            merged_df.at[idx, "summary"] = lookup[url].get("summary", "")
            merged_df.at[idx, "topics"] = ", ".join(lookup[url].get("topics", []))

    return merged_df


def scrape_all_sites(max_workers: int = 2):
    total_sites = len(SITES)
    total_rows = 0
    processed_sites = 0

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

            merged_df = merge_with_cache(raw_df)
            merged_df = enrich_with_llm(raw_df, merged_df, site_url)

            save_cache(merged_df)

            total_rows += len(raw_df)
            processed_sites += 1
            overall.progress(processed_sites / total_sites,
                             text=f"Processed {processed_sites}/{total_sites} sites")

    overall.empty()
    st.session_state["cancel_scrape"] = False
    st.success(f"✅ Full run complete. Added/updated {total_rows} rows across {processed_sites} sites.")


def scrape_site_with_cache(site_url: str) -> pd.DataFrame:
    raw_df = scrape_site(site_url)
    merged_df = merge_with_cache(raw_df)
    merged_df = enrich_with_llm(raw_df, merged_df, site_url)
    save_cache(merged_df)
    return merged_df

