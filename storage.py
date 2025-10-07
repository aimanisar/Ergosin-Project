#!/usr/bin/env python3
"""
Data Storage Module for Competitive Intelligence Dashboard.

This module handles all data persistence operations including:
- Milvus vector database integration for data storage
- Data merging and caching functionality
- Content hashing for change detection
- Error handling and fallback mechanisms
"""

import pandas as pd
import hashlib

from milvus_storage import get_milvus_storage

def make_hash(text: str) -> str:
    """Generate MD5 hash of text for change detection."""
    return hashlib.md5((text or "").encode("utf-8")).hexdigest()


def load_cache() -> pd.DataFrame:
    """Load existing data from Milvus into a DataFrame, or return empty DataFrame if none exists."""
    try:
        milvus_storage = get_milvus_storage()
        return milvus_storage.load_cache()
    except Exception as e:
        import streamlit as st
        
        st.error(f"Error loading from Milvus: {e}")
        st.info("**Possible Solutions:**")
        st.info("1. **Make sure Milvus is running** on localhost:19530")
        st.info("2. **Check your Milvus connection settings** in config.py")
        st.info("3. **Restart the application**")
        st.info("4. **Install Milvus** if not already installed")
        
        # Show a retry button
        if st.button("🔄 Retry Connection", key="retry_milvus"):
            st.rerun()
        
        # Fallback to empty DataFrame
        return pd.DataFrame(columns=[
            "website", "page_url", "page_name",
            "content", "content_hash", "summary", "topics", "last_scraped"
        ])


def save_cache(df: pd.DataFrame) -> None:
    """Save DataFrame to Milvus, overwriting the old cache."""
    if df is None or df.empty:
        return
    try:
        milvus_storage = get_milvus_storage()
        milvus_storage.save_cache(df)
    except Exception as e:
        import streamlit as st
        st.error(f"Error saving to Milvus: {e}")


def merge_with_cache(new_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge new scraped rows with existing cache from Milvus.
    Always keeps the latest version of each page_url.
    """
    try:
        milvus_storage = get_milvus_storage()
        return milvus_storage.merge_with_cache(new_df)
    except Exception as e:
        import streamlit as st
        st.error(f"Error merging with Milvus cache: {e}")
        # Fallback to just returning the new data
        return new_df
