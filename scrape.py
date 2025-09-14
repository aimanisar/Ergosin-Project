# scrape.py
"""
Handles scraping logic:
- Launching headless Chrome with Selenium
- Extracting and cleaning page content
- Extracting internal links
- Scraping full site (main + subpages)
"""

import time
from urllib.parse import urljoin, urlparse

import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from llm_process import filter_links_with_llm
from storage import load_cache, make_hash  

# ------------------ Core Page Scraping ------------------

def scrape_website(website, wait_time=10, scroll_pause=2):
    """Launch headless Chrome, scroll to bottom, return raw HTML."""
    print(f"Launching headless Chrome browser for: {website}")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(website)

        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Scroll to load lazy content
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        return driver.page_source

    finally:
        driver.quit()


def extract_main_content(html_content: str) -> str:
    """Extract main readable text content from HTML."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove boilerplate
    for tag in soup(["header", "footer", "nav", "script", "style", "noscript"]):
        tag.decompose()

    # Prefer semantic containers
    if (main_tag := soup.find("main")):
        return main_tag.get_text(separator="\n", strip=True)

    if (article_tag := soup.find("article")):
        return article_tag.get_text(separator="\n", strip=True)

    # Fallback: largest <div>
    divs = soup.find_all("div")
    if divs:
        largest_div = max(divs, key=lambda d: len(d.get_text()))
        return largest_div.get_text(separator="\n", strip=True)

    # Last fallback: all body text
    return soup.get_text(separator="\n", strip=True)


def extract_internal_links(html_content: str, base_url: str) -> list[str]:
    """Extract internal links belonging to the same domain."""
    soup = BeautifulSoup(html_content, "html.parser")
    links = set()
    base_domain = urlparse(base_url).netloc

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith(("mailto:", "tel:", "#")):
            continue

        full_url = urljoin(base_url, href)
        if urlparse(full_url).netloc == base_domain:
            links.add(full_url)

    return list(links)


# ------------------ Site-level Scraping ------------------

def scrape_site(site_url: str) -> pd.DataFrame:
    """Scrape a site (main + internal pages), skipping unchanged ones."""
    domain = urlparse(site_url).netloc
    rows = []

    status = st.empty()
    url_log = st.container()
    prog = st.progress(0, text=f"Starting: {site_url}")

    def _log(msg: str):
        status.write(msg)
        with url_log:
            st.write(msg)

    now = pd.Timestamp.utcnow().isoformat()

    # --- Main page ---
    _log(f"🔎 Checking main page: {site_url}")
    main_row = scrape_page_if_changed(site_url, domain, "home", now)
    if main_row:
        rows.append(main_row)

    # --- Internal subpages ---
    main_html = scrape_website(site_url)  # still needed to extract links
    subpages = extract_internal_links(main_html, site_url)

    # Deduplicate + LLM filter
    seen = set()
    subpages = [u for u in subpages if not (u in seen or seen.add(u))]
    subpages = filter_links_with_llm(subpages, site_url)

    total = max(1, len(subpages) + 1)
    done = 1
    prog.progress(done / total, text=f"{domain}: {done}/{total}")

    for sub_url in subpages:
        sub_name = urlparse(sub_url).path.strip("/") or "home"
        row = scrape_page_if_changed(sub_url, domain, sub_name, now)
        if row:
            rows.append(row)
            _log(f"✅ Updated: {sub_url}")
        else:
            _log(f"⏭️ No change: {sub_url}")

        done += 1
        prog.progress(min(done / total, 1.0), text=f"{domain}: {done}/{total}")

    prog.empty()
    status.empty()

    return pd.DataFrame(
        rows,
        columns=["website", "page_url", "page_name", "content",
                 "content_hash", "summary", "topics", "last_scraped"]
    )


# --------------Hash based comparison for unchanged pages ---------------
def scrape_page_if_changed(url: str, domain: str, page_name: str, now: str):
    """
    Scrape a page only if content has changed (by hash).
    Returns a row dict or None if unchanged.
    """
    cache = load_cache()
    cached_row = cache[cache["page_url"] == url]

    if not cached_row.empty:
        # If cached, check hash
        old_hash = cached_row.iloc[0]["content_hash"]
        old_content = cached_row.iloc[0]["content"]

        # Hash the cached content
        if old_hash == make_hash(old_content or ""):
            print(f"⏭️ Skipping unchanged: {url}")
            return None  # unchanged, skip scraping

    # Otherwise → scrape fresh
    html = scrape_website(url)
    clean = extract_main_content(html)
    clean = clean.replace("\n", " ").replace("\r", " ").strip()

    return {
        "website": domain,
        "page_url": url,
        "page_name": page_name,
        "content": clean,
        "content_hash": make_hash(clean),
        "summary": "",
        "topics": "",
        "last_scraped": now
    }




# import selenium.webdriver as webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.options import Options
# from bs4 import BeautifulSoup
# import time
# from urllib.parse import urljoin, urlparse

# def scrape_website(website, wait_time=10, scroll_pause=2):
#     # print(f"Launching headless Chrome browser for: {website}")

#     # chrome_driver_path = "./chromedriver"
#     # options = webdriver.ChromeOptions()
#     # options.add_argument("--headless")
#     # options.add_argument("--no-sandbox")
#     # options.add_argument("--disable-dev-shm-usage")

#     # driver = webdriver.Chrome(service=Service(chrome_driver_path), options=options)

#     print(f"Launching headless Chrome browser for: {website}")

#     options = Options()
#     options.add_argument("--headless=new")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")

#     # Selenium Manager will download the correct Windows driver automatically
#     driver = webdriver.Chrome(options=options)

#     try:
#         driver.get(website)

#         WebDriverWait(driver, wait_time).until(
#             EC.presence_of_element_located((By.TAG_NAME, "body"))
#         )

#         last_height = driver.execute_script("return document.body.scrollHeight")
#         while True:
#             driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#             time.sleep(scroll_pause)
#             new_height = driver.execute_script("return document.body.scrollHeight")
#             if new_height == last_height:
#                 break
#             last_height = new_height

#         html = driver.page_source
#         return html

#     finally:
#         driver.quit()


# def extract_main_content(html_content):
#     soup = BeautifulSoup(html_content, "html.parser")

#     # Remove common boilerplate elements (headers, footers, nav, scripts, styles)
#     for tag in soup(["header", "footer", "nav", "script", "style", "noscript"]):
#         tag.decompose()

#     # First try <main>
#     main_tag = soup.find("main")
#     if main_tag:
#         return main_tag.get_text(separator="\n", strip=True)

#     # Then try <article>
#     article_tag = soup.find("article")
#     if article_tag:
#         return article_tag.get_text(separator="\n", strip=True)

#     # If no semantic tag, find largest <div>
#     divs = soup.find_all("div")
#     if divs:
#         largest_div = max(divs, key=lambda d: len(d.get_text()))
#         return largest_div.get_text(separator="\n", strip=True)

#     # Fallback: return entire cleaned body
#     return soup.get_text(separator="\n", strip=True)


# def split_dom_content(dom_content, max_length=6000):
#     return [
#         dom_content[i : i + max_length] for i in range(0, len(dom_content), max_length)
#     ]


# def extract_internal_links(html_content, base_url):
#     soup = BeautifulSoup(html_content, "html.parser")
#     links = set()
#     base_domain = urlparse(base_url).netloc

#     for a in soup.find_all("a", href=True):
#         href = a["href"]

#         if href.startswith(("mailto:", "tel:", "#")):
#             continue

#         full_url = urljoin(base_url, href)

#         if urlparse(full_url).netloc == base_domain:
#             links.add(full_url)

#     return list(links)

