#!/usr/bin/env python3
"""
Google Sheets Integration Module for Competitive Intelligence Dashboard.

This module provides Google Sheets integration for data persistence:
- Service Account authentication
- Data reading and writing operations
- Error handling and SSL management
- Automatic sheet creation and management
"""

import os
import json
import time
import ssl
from typing import Optional

import pandas as pd
import streamlit as st
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleSheetsStorage:
    def __init__(self, spreadsheet_id: str, sheet_name: str = "Sheet1"):
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API using Service Account."""
        if not os.path.exists('credentials.json'):
            st.error("""
            **Google Sheets Setup Required:**
            
            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Create a new project or select existing one
            3. Enable Google Sheets API
            4. Create credentials (Service Account) 
            5. Download the service account JSON file and save as 'credentials.json' in this directory
            6. Share your Google Sheet with the service account email
            7. Restart the application
            """)
            st.stop()
        
        try:
            # Load service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                'credentials.json',
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            self.service = build('sheets', 'v4', credentials=credentials)
        except Exception as e:
            st.error(f"Error loading service account credentials: {e}")
            st.stop()
    
    def _get_sheet_data(self) -> pd.DataFrame:
        """Get all data from the Google Sheet."""
        try:
            range_name = f'{self.sheet_name}!A:H'  # Adjust range based on your columns
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range=range_name).execute()
            values = result.get('values', [])
            
            if not values:
                return pd.DataFrame(columns=[
                    "website", "page_url", "page_name",
                    "content", "content_hash", "summary", "topics", "last_scraped"
                ])
            
            # First row as headers
            headers = values[0]
            data = values[1:] if len(values) > 1 else []
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=headers)
            
            # Ensure all expected columns exist
            expected_columns = [
                "website", "page_url", "page_name",
                "content", "content_hash", "summary", "topics", "last_scraped"
            ]
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = ""
            
            # Convert topics from JSON string back to list
            if "topics" in df.columns:
                df["topics"] = df["topics"].apply(
                    lambda x: json.loads(x) if isinstance(x, str) and x.startswith("[") else (x if isinstance(x, str) and x else [])
                )
            
            return df
            
        except HttpError as error:
            st.error(f"Error reading from Google Sheets: {error}")
            return pd.DataFrame(columns=[
                "website", "page_url", "page_name",
                "content", "content_hash", "summary", "topics", "last_scraped"
            ])
    
    def _save_sheet_data(self, df: pd.DataFrame) -> None:
        """Save DataFrame to Google Sheet."""
        if df is None or df.empty:
            return
        
        try:
            # Convert topics back to JSON string for storage
            df_copy = df.copy()
            if "topics" in df_copy.columns:
                df_copy["topics"] = df_copy["topics"].apply(
                    lambda x: json.dumps(x) if isinstance(x, list) else (x if isinstance(x, str) else "")
                )
            
            # Prepare data for Google Sheets
            values = [df_copy.columns.tolist()] + df_copy.values.tolist()
            
            # Clear existing data and write new data
            range_name = f'{self.sheet_name}!A1'
            body = {'values': values}
            
            # Clear the sheet first
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A:Z'
            ).execute()
            
            # Write new data
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
        except HttpError as error:
            st.error(f"Error saving to Google Sheets: {error}")
    
    def load_cache(self) -> pd.DataFrame:
        """Load existing data from Google Sheet into a DataFrame."""
        return self._get_sheet_data()
    
    def save_cache(self, df: pd.DataFrame) -> None:
        """Save DataFrame to Google Sheet, overwriting the old data."""
        self._save_sheet_data(df)
    
    def merge_with_cache(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge new scraped rows with existing cache from Google Sheets.
        Always keeps the latest version of each page_url.
        """
        cached_df = self.load_cache()
        merged_df = pd.concat([cached_df, new_df], ignore_index=True)
        
        # Drop duplicates keeping the most recent scrape
        merged_df = merged_df.drop_duplicates(subset=["page_url"], keep="last")
        
        return merged_df

# Global instance - will be initialized in main.py
sheets_storage: Optional[GoogleSheetsStorage] = None

def get_sheets_storage() -> GoogleSheetsStorage:
    """Get the global Google Sheets storage instance."""
    global sheets_storage
    if sheets_storage is None:
        from config import GOOGLE_SHEETS_ID
        sheets_storage = GoogleSheetsStorage(GOOGLE_SHEETS_ID)
    return sheets_storage
