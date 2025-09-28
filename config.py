#!/usr/bin/env python3
"""
Configuration file for the Competitive Intelligence Dashboard.

This module contains all configuration constants including:
- Data storage paths
- Website lists for scraping
- Blocked URL patterns
- Google Sheets integration settings
"""

# Google Sheets configuration
GOOGLE_SHEETS_ID = "1OT97TTg0OnH-eFnRmw3-FAxrctFxB6BwB739A97fvbg"

# List of sites to scrape (base + competitors)
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
    {"type": "competitor", "url": "https://www.uid.com/en/"},
    {"type": "competitor", "url": "https://www.consulteer.com/"},
    {"type": "competitor", "url": "https://www.404.agency/hr/"},
    {"type": "competitor", "url": "https://www.custom-interactions.com/"},
    {"type": "competitor", "url": "https://www.wikipedia.org/"}
]

# Paths or keywords that should be blocked from scraping
BLOCKED_BASES = [
    "/career", "/careers", "/about", "/cookies", "/subscribe",
    "/privacy", "/terms", "/legal", "/impressum",
    "/karriere", "/jobs", "/ueber-uns", "/unternehmen",
    "/team", "/contact", "/studios"
]
