#!/usr/bin/env python3
"""
Configuration file for the Competitive Intelligence Dashboard.

This module contains all configuration constants including:
- Data storage paths
- Website lists for scraping
- Blocked URL patterns
- Google Sheets integration settings
"""

# Milvus configuration (Zilliz Cloud)
MILVUS_HOST = "in03-b7890c38c8613f7.serverless.aws-eu-central-1.cloud.zilliz.com"
MILVUS_PORT = "443"  # HTTPS port for Zilliz Cloud
MILVUS_COLLECTION_NAME = "scraped_data"  # New collection matching Google Sheets schema
MILVUS_DIMENSION = 768  # Standard embedding dimension
MILVUS_LITE = False  # Use Zilliz Cloud
MILVUS_TOKEN = "2b7fdfd0b0b9be5be2b4ba4eb2a9126e2d6b5b52da4c4ec09a0c32cff1ac96c657aa5bb38a74beada6c92dfc59a5d578daf13db9"

# Google Sheets configuration (disabled)
# GOOGLE_SHEETS_ID = "1OT97TTg0OnH-eFnRmw3-FAxrctFxB6BwB739A97fvbg"

# List of sites to scrape (base + competitors)
SITES = [
    {"type": "base", "url": "https://ergosign.de/"},
    {"type": "competitor_close", "url": "https://www.cobeisfresh.com/"},
    {"type": "competitor_close", "url": "https://www.designaffairs.com/"},
    {"type": "competitor_close", "url": "https://www.designit.com/"},
    {"type": "competitor_close", "url": "https://www.diva-e.com/de/"},
    {"type": "competitor_close", "url": "https://www.centigrade.de/de/"},
    {"type": "competitor_close", "url": "https://www.shapefield.de/shape/welcome"},
    {"type": "competitor_close", "url": "https://www.uid.com/en/"},
    {"type": "competitor_international", "url": "https://www.frogdesign.com/"},
    {"type": "competitor_international", "url": "https://www.futurice.com/"},
    {"type": "competitor_international", "url": "https://ginetta.net/"},
    {"type": "competitor_international", "url": "https://www.ideo.com/eu"},
    {"type": "competitor_international", "url": "https://www.phoenixdesign.com/"},
    {"type": "competitor_international", "url": "https://www.consulteer.com/"},
    {"type": "competitor_international", "url": "https://www.404.agency/hr/"},
    {"type": "competitor_international", "url": "https://www.custom-interactions.com/"},
]

# Paths or keywords that should be blocked from scraping
BLOCKED_BASES = [
    "/career", "/careers", "/about", "/cookies", "/subscribe",
    "/privacy", "/terms", "/legal", "/impressum",
    "/karriere", "/jobs", "/ueber-uns", "/unternehmen",
    "/team", "/contact", "/studios"
]
