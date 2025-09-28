#!/usr/bin/env python3
"""
Data Storage Module for Competitive Intelligence Dashboard.

This module handles all data persistence operations including:
- Google Sheets integration for data storage
- Data merging and caching functionality
- Content hashing for change detection
- Error handling and fallback mechanisms
"""

import pandas as pd
import hashlib

from google_sheets_storage import get_sheets_storage

def make_hash(text: str) -> str:
    """Generate MD5 hash of text for change detection."""
    return hashlib.md5((text or "").encode("utf-8")).hexdigest()


def load_cache() -> pd.DataFrame:
    """Load existing data from Google Sheets into a DataFrame, or return empty DataFrame if none exists."""
    try:
        sheets_storage = get_sheets_storage()
        return sheets_storage.load_cache()
    except Exception as e:
        import streamlit as st
        import ssl
        
        # Check if it's an SSL error
        if isinstance(e, ssl.SSLError) or "SSL" in str(e) or "DECRYPTION_FAILED" in str(e):
            st.warning("🔒 **SSL Connection Issue Detected**")
            st.info("**Possible Solutions:**")
            st.info("1. **Check your internet connection**")
            st.info("2. **Try using a VPN** if you're behind a corporate firewall")
            st.info("3. **Restart your application**")
            st.info("4. **Update your Python SSL certificates**")
            st.info("5. **Try again in a few minutes** - this might be a temporary network issue")
            
            # Show a retry button
            if st.button("🔄 Retry Connection", key="retry_ssl"):
                st.rerun()
        else:
            st.error(f"Error loading from Google Sheets: {e}")
        
        # Fallback to empty DataFrame
        return pd.DataFrame(columns=[
            "website", "page_url", "page_name",
            "content", "content_hash", "summary", "topics", "last_scraped"
        ])


def save_cache(df: pd.DataFrame) -> None:
    """Save DataFrame to Google Sheets, overwriting the old cache."""
    if df is None or df.empty:
        return
    try:
        sheets_storage = get_sheets_storage()
        sheets_storage.save_cache(df)
    except Exception as e:
        import streamlit as st
        st.error(f"Error saving to Google Sheets: {e}")


def merge_with_cache(new_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge new scraped rows with existing cache from Google Sheets.
    Always keeps the latest version of each page_url.
    """
    try:
        sheets_storage = get_sheets_storage()
        return sheets_storage.merge_with_cache(new_df)
    except Exception as e:
        import streamlit as st
        st.error(f"Error merging with Google Sheets cache: {e}")
        # Fallback to just returning the new data
        return new_df
