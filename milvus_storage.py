#!/usr/bin/env python3
"""
Milvus Vector Database Integration Module for Competitive Intelligence Dashboard.

This module provides Milvus integration for data persistence:
- Vector database connection and management
- Data insertion and retrieval operations
- Collection schema management
- Error handling and connection management
"""

import os
import json
import time
import hashlib
from typing import Optional, List, Dict, Any
import pandas as pd
import streamlit as st

from pymilvus import (
    connections, Collection, CollectionSchema, FieldSchema, DataType,
    utility, MilvusException
)

class MilvusStorage:
    def __init__(self, host: str = "localhost", port: str = "19530", collection_name: str = "scraped_data", use_lite: bool = True, token: str = None):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.use_lite = use_lite
        self.token = token
        self.collection = None
        self._connect()
        self._setup_collection()
    
    def _connect(self):
        """Connect to Milvus database."""
        try:
            # Connect to Milvus server (Zilliz Cloud or local)
            if self.token:
                # Zilliz Cloud connection with token
                connections.connect(
                    alias="default",
                    uri=f"https://{self.host}",
                    token=self.token
                )
                # st.success(f"✅ Connected to Zilliz Cloud Milvus")
            else:
                # Local Milvus connection
                connections.connect(
                    alias="default",
                    host=self.host,
                    port=self.port
                )
                # st.success(f"✅ Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            st.error(f"❌ Failed to connect to Milvus: {e}")
            if self.token:
                st.info("""
                **Zilliz Cloud Connection Issue:**
                
                1. Check your internet connection
                2. Verify the token is correct
                3. Ensure the cluster is running
                4. Check Zilliz Cloud dashboard for status
                """)
            else:
                st.info("""
                **Milvus Server Setup Required:**
                
                1. Install and start Milvus using Docker:
                   ```bash
                   docker run -d --name milvus-standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest
                   ```
                
                2. Wait 10-15 seconds for Milvus to start
                
                3. Verify Milvus is running:
                   ```bash
                   docker ps | grep milvus
                   ```
                
                4. Restart the application
                """)
            st.stop()
    
    def _setup_collection(self):
        """Set up the collection schema and create if it doesn't exist."""
        try:
            # Check if collection already exists (for Zilliz Cloud)
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                # st.info(f"📊 Using existing collection: {self.collection_name}")
                self.collection.load()
                return
            
            # Define collection schema (matching Google Sheets structure exactly)
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="website", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="page_url", dtype=DataType.VARCHAR, max_length=1000),
                FieldSchema(name="page_name", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="content_hash", dtype=DataType.VARCHAR, max_length=32),
                FieldSchema(name="summary", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="topics", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="last_scraped", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="content_vector", dtype=DataType.FLOAT_VECTOR, dim=768)  # For similarity search
            ]
            
            schema = CollectionSchema(fields, f"Collection for storing scraped website data")
            
            # Check if collection exists
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                # st.info(f"📊 Using existing collection: {self.collection_name}")
            else:
                # Create collection
                self.collection = Collection(self.collection_name, schema)
                st.success(f"✅ Created new collection: {self.collection_name}")
            
            # Create index for vector field (required for search)
            if not self.collection.has_index():
                index_params = {
                    "metric_type": "L2",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 128}
                }
                self.collection.create_index("content_vector", index_params)
                st.info("🔍 Created vector index for content search")
            
            # Load collection into memory
            self.collection.load()
            
        except MilvusException as e:
            st.error(f"❌ Error setting up Milvus collection: {e}")
            st.stop()
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate a simple embedding for the text.
        In a production environment, you would use a proper embedding model like sentence-transformers.
        For now, we'll use a simple hash-based approach.
        """
        # Simple hash-based embedding (replace with proper embedding model in production)
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to 768-dimensional vector (standard embedding dimension)
        embedding = []
        for i in range(0, len(hash_bytes), 4):
            if len(embedding) >= 768:
                break
            # Convert 4 bytes to float
            val = int.from_bytes(hash_bytes[i:i+4], byteorder='big')
            # Normalize to [-1, 1] range
            normalized = (val / (2**32 - 1)) * 2 - 1
            embedding.append(normalized)
        
        # Pad to 768 dimensions if needed
        while len(embedding) < 768:
            embedding.append(0.0)
        
        return embedding[:768]
    
    def _dataframe_to_milvus_data(self, df: pd.DataFrame) -> List[List]:
        """Convert DataFrame to Milvus insert format."""
        # Milvus expects data as separate lists for each field (column-based format)
        websites = []
        page_urls = []
        page_names = []
        contents = []
        content_hashes = []
        summaries = []
        topics = []
        last_scraped = []
        content_vectors = []
        
        for _, row in df.iterrows():
            # Generate embedding for content
            content_text = str(row.get("content", ""))
            content_embedding = self._generate_embedding(content_text)
            
            # Add to respective field lists
            websites.append(str(row.get("website", "")))
            page_urls.append(str(row.get("page_url", "")))
            page_names.append(str(row.get("page_name", "")))
            contents.append(str(row.get("content", "")))
            content_hashes.append(str(row.get("content_hash", "")))
            summaries.append(str(row.get("summary", "")))
            topics.append(str(row.get("topics", "")))
            last_scraped.append(str(row.get("last_scraped", "")))
            content_vectors.append(content_embedding)
        
        # Return data in column-based format (list of field lists)
        return [
            websites,      # website
            page_urls,     # page_url
            page_names,    # page_name
            contents,      # content
            content_hashes, # content_hash
            summaries,     # summary
            topics,        # topics
            last_scraped,  # last_scraped
            content_vectors # content_vector
        ]
    
    def _milvus_data_to_dataframe(self, results: List) -> pd.DataFrame:
        """Convert Milvus query results to DataFrame."""
        if not results:
            return pd.DataFrame(columns=[
                "website", "page_url", "page_name",
                "content", "content_hash", "summary", "topics", "last_scraped"
            ])
        
        data = []
        for result in results:
            row = {
                "website": result.get("website", ""),
                "page_url": result.get("page_url", ""),
                "page_name": result.get("page_name", ""),
                "content": result.get("content", ""),
                "content_hash": result.get("content_hash", ""),
                "summary": result.get("summary", ""),
                "topics": result.get("topics", ""),
                "last_scraped": result.get("last_scraped", "")
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Convert topics from JSON string back to list if needed
        if "topics" in df.columns:
            df["topics"] = df["topics"].apply(
                lambda x: json.loads(x) if isinstance(x, str) and x.startswith("[") else (x if isinstance(x, str) and x else [])
            )
        
        return df
    
    def load_cache(self) -> pd.DataFrame:
        """Load all data from Milvus collection into a DataFrame."""
        try:
            # Query all data (excluding vector fields for DataFrame)
            # Use a large limit to get all records
            results = self.collection.query(
                expr="",  # Empty expression means get all
                output_fields=["website", "page_url", "page_name", "content", "content_hash", "summary", "topics", "last_scraped"],
                limit=16384  # Large limit to get all records
            )
            
            return self._milvus_data_to_dataframe(results)
            
        except MilvusException as e:
            st.error(f"❌ Error loading from Milvus: {e}")
            return pd.DataFrame(columns=[
                "website", "page_url", "page_name",
                "content", "content_hash", "summary", "topics", "last_scraped"
            ])
    
    def save_cache(self, df: pd.DataFrame) -> None:
        """Save DataFrame to Milvus collection, replacing all existing data."""
        if df is None or df.empty:
            return
        
        try:
            # Convert DataFrame to Milvus format
            data = self._dataframe_to_milvus_data(df)
            
            # Insert new data (data is now a list of field lists - column-based format)
            if data and len(data[0]) > 0:  # Check if we have data and at least one record
                # Clear existing data first (since we're doing a full replacement)
                # Use a valid filter expression to delete all records
                try:
                    self.collection.delete(expr="id > 0")
                except:
                    # If delete fails, continue with insert (might be empty collection)
                    pass
                
                self.collection.insert(data)
                self.collection.flush()  # Ensure data is persisted
                st.success(f"✅ Saved {len(data[0])} records to Milvus")
            
        except MilvusException as e:
            st.error(f"❌ Error saving to Milvus: {e}")
    
    def merge_with_cache(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge new scraped rows with existing cache from Milvus.
        Uses content_hash to detect changes and avoid duplicates.
        """
        try:
            # Load existing data
            cached_df = self.load_cache()
            
            if cached_df.empty:
                # No existing data, just return new data
                return new_df
            
            # Check for changes using content_hash
            updated_records = []
            new_records = []
            
            for _, new_row in new_df.iterrows():
                new_hash = new_row.get("content_hash", "")
                new_url = new_row.get("page_url", "")
                
                # Check if this URL exists in cache
                existing_rows = cached_df[cached_df["page_url"] == new_url]
                
                if not existing_rows.empty:
                    # URL exists, check if content has changed
                    existing_hash = existing_rows.iloc[0].get("content_hash", "")
                    
                    if new_hash != existing_hash:
                        # Content has changed, this is an update
                        updated_records.append(new_row)
                        st.info(f"🔄 Content updated for: {new_url}")
                    else:
                        # No changes, skip this record
                        st.info(f"⏭️ No changes detected for: {new_url}")
                else:
                    # New URL, this is a new record
                    new_records.append(new_row)
                    # st.info(f"➕ New page found: {new_url}")
            
            if not updated_records and not new_records:
                st.success("✅ No new or updated content found. No database changes needed.")
                return cached_df
            
            # Create updated dataframe
            if updated_records or new_records:
                # Remove old versions of updated records
                updated_urls = [row["page_url"] for row in updated_records]
                cached_df = cached_df[~cached_df["page_url"].isin(updated_urls)]
                
                # Add new and updated records
                all_new_data = updated_records + new_records
                new_data_df = pd.DataFrame(all_new_data)
                
                # Combine cached data with new/updated data
                merged_df = pd.concat([cached_df, new_data_df], ignore_index=True)
                
                st.success(f"📊 Database update: {len(updated_records)} updated, {len(new_records)} new records")
                return merged_df
            else:
                return cached_df
            
        except Exception as e:
            st.error(f"❌ Error merging with Milvus cache: {e}")
            # Fallback to just returning the new data
            return new_df
    
    def cleanup_duplicates(self) -> None:
        """
        Clean up duplicate entries in the database based on page_url.
        Keeps the most recent entry for each URL.
        """
        try:
            # Load all data
            df = self.load_cache()
            
            if df.empty:
                st.info("📊 No data to clean up")
                return
            
            # Count duplicates
            initial_count = len(df)
            df_cleaned = df.drop_duplicates(subset=["page_url"], keep="last")
            final_count = len(df_cleaned)
            duplicates_removed = initial_count - final_count
            
            if duplicates_removed > 0:
                # Save cleaned data back to Milvus
                self.save_cache(df_cleaned)
                st.success(f"🧹 Cleaned up {duplicates_removed} duplicate entries")
            else:
                st.info("✅ No duplicates found")
                
        except Exception as e:
            st.error(f"❌ Error cleaning up duplicates: {e}")

    def search_similar_content(self, query_text: str, limit: int = 10) -> pd.DataFrame:
        """
        Search for similar content using vector similarity.
        This is a bonus feature that leverages Milvus's vector search capabilities.
        """
        try:
            # Generate embedding for query
            query_embedding = self._generate_embedding(query_text)
            
            # Search for similar vectors using content_vector field
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            results = self.collection.search(
                data=[query_embedding],
                anns_field="content_vector",  # Use the correct field name from our schema
                param=search_params,
                limit=limit,
                output_fields=["website", "page_url", "page_name", "content", "summary", "topics"]
            )
            
            # Convert results to DataFrame
            data = []
            for hits in results:
                for hit in hits:
                    data.append({
                        "website": hit.entity.get("website", ""),
                        "page_url": hit.entity.get("page_url", ""),
                        "page_name": hit.entity.get("page_name", ""),
                        "content": hit.entity.get("content", ""),
                        "summary": hit.entity.get("summary", ""),
                        "topics": hit.entity.get("topics", ""),
                        "similarity_score": hit.score
                    })
            
            return pd.DataFrame(data)
            
        except MilvusException as e:
            st.error(f"❌ Error searching Milvus: {e}")
            return pd.DataFrame()

# Global instance - will be initialized in main.py
milvus_storage: Optional[MilvusStorage] = None

def get_milvus_storage() -> MilvusStorage:
    """Get the global Milvus storage instance."""
    global milvus_storage
    if milvus_storage is None:
        from config import MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION_NAME, MILVUS_LITE, MILVUS_TOKEN
        milvus_storage = MilvusStorage(MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION_NAME, MILVUS_LITE, MILVUS_TOKEN)
    return milvus_storage
