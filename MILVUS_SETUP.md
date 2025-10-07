# Milvus Integration Setup Guide

This guide explains how to set up and use Milvus vector database instead of Google Sheets for data storage in the Competitive Intelligence Dashboard.

## What Changed

- **Storage Backend**: Switched from Google Sheets to Milvus vector database
- **New Features**: Added vector search capabilities for content similarity
- **Configuration**: Updated `config.py` with Milvus settings
- **Dependencies**: Replaced Google Sheets dependencies with `pymilvus`

## Quick Setup

### Option 1: Automated Setup (Recommended)
```bash
python setup_milvus.py
```

### Option 2: Manual Docker Setup
```bash
# Start Milvus with Docker
docker run -d --name milvus-standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest

# Install Python dependencies
pip install -r requirements.txt
```

### Option 3: Manual Pip Setup
```bash
# Install pymilvus
pip install pymilvus>=2.3.0

# Install other dependencies
pip install -r requirements.txt
```

## Configuration

The Milvus configuration is in `config.py`:

```python
# Milvus configuration
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
MILVUS_COLLECTION_NAME = "scraped_data"
MILVUS_DIMENSION = 768  # For text embeddings
```

## Running the Application

1. **Start Milvus** (if using Docker):
   ```bash
   docker start milvus-standalone
   ```

2. **Run the application**:
   ```bash
   streamlit run main.py
   ```

## New Features

### Vector Search
The Milvus integration includes a bonus feature for content similarity search:

```python
from milvus_storage import get_milvus_storage

# Search for similar content
milvus = get_milvus_storage()
similar_pages = milvus.search_similar_content("design agency", limit=5)
```

### Data Schema
The Milvus collection stores:
- **website**: Source website URL
- **page_url**: Individual page URL
- **page_name**: Page title
- **content**: Full page content
- **content_hash**: MD5 hash for change detection
- **summary**: AI-generated summary
- **topics**: Extracted topics
- **last_scraped**: Timestamp
- **content_vector**: 768-dimensional embedding for similarity search

## Troubleshooting

### Connection Issues
- Ensure Milvus is running on `localhost:19530`
- Check Docker container status: `docker ps`
- Restart Milvus: `docker restart milvus-standalone`

### Performance
- For production, consider using Milvus with more resources
- Adjust `MILVUS_DIMENSION` based on your embedding model
- Monitor memory usage with large datasets

### Data Migration
- Existing Google Sheets data can be exported and imported
- Use the CSV download feature to backup data
- Import CSV data through the application interface

## Benefits of Milvus

1. **Vector Search**: Find similar content across all scraped pages
2. **Scalability**: Better performance with large datasets
3. **Local Storage**: No external API dependencies
4. **Advanced Queries**: Complex filtering and search capabilities
5. **Real-time Updates**: Faster data insertion and retrieval

## Reverting to Google Sheets

If you need to revert to Google Sheets:

1. **Uncomment the Google Sheets configuration** in `config.py`:
   ```python
   # Change this line:
   # GOOGLE_SHEETS_ID = "1OT97TTg0OnH-eFnRmw3-FAxrctFxB6BwB739A97fvbg"
   # To this:
   GOOGLE_SHEETS_ID = "1OT97TTg0OnH-eFnRmw3-FAxrctFxB6BwB739A97fvbg"
   ```

2. **Comment out the Milvus configuration** in `config.py`:
   ```python
   # Comment out these lines:
   # MILVUS_HOST = "localhost"
   # MILVUS_PORT = "19530"
   # MILVUS_COLLECTION_NAME = "scraped_data"
   # MILVUS_DIMENSION = 768
   ```

3. **Restore the original `storage.py` imports**:
   ```python
   # Change from:
   from milvus_storage import get_milvus_storage
   # Back to:
   from google_sheets_storage import get_sheets_storage
   ```

4. **Install Google Sheets dependencies**:
   ```bash
   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
   ```

5. **Restore the original `storage.py` function implementations** to use Google Sheets instead of Milvus

## Support

For issues with Milvus setup or integration, check:
- [Milvus Documentation](https://milvus.io/docs)
- [PyMilvus Documentation](https://pymilvus.readthedocs.io/)
- Application logs for specific error messages
