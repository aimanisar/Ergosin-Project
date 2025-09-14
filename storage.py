# storage.py
"""
Handles data persistence for the scraper:
- Saving and loading CSVs
- Merging new scraped data with existing cache
- Hashing content for change detection
"""

import os
import pandas as pd
import hashlib
from config import CSV_PATH


def make_hash(text: str) -> str:
    """Generate MD5 hash of text for change detection."""
    return hashlib.md5((text or "").encode("utf-8")).hexdigest()


def load_cache() -> pd.DataFrame:
    """Load existing CSV into a DataFrame, or return empty DataFrame if none exists."""
    if os.path.exists(CSV_PATH):
        return pd.read_csv(CSV_PATH)
    return pd.DataFrame(columns=[
        "website", "page_url", "page_name",
        "content", "content_hash", "summary", "topics", "last_scraped"
    ])


def save_cache(df: pd.DataFrame) -> None:
    """Save DataFrame to CSV, overwriting the old cache."""
    if df is None or df.empty:
        return
    df.to_csv(CSV_PATH, index=False, encoding="utf-8")


def merge_with_cache(new_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge new scraped rows with existing cache.
    Always keeps the latest version of each page_url.
    """
    cached_df = load_cache()
    merged_df = pd.concat([cached_df, new_df], ignore_index=True)

    # Drop duplicates keeping the most recent scrape
    merged_df = merged_df.drop_duplicates(subset=["page_url"], keep="last")

    return merged_df
