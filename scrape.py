import selenium.webdriver as webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, urlparse

def scrape_website(website, wait_time=10, scroll_pause=2):
    # print(f"Launching headless Chrome browser for: {website}")

    # chrome_driver_path = "./chromedriver"
    # options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    # options.add_argument("--no-sandbox")
    # options.add_argument("--disable-dev-shm-usage")

    # driver = webdriver.Chrome(service=Service(chrome_driver_path), options=options)

    print(f"Launching headless Chrome browser for: {website}")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Selenium Manager will download the correct Windows driver automatically
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(website)

        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        html = driver.page_source
        return html

    finally:
        driver.quit()


def extract_main_content(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove common boilerplate elements (headers, footers, nav, scripts, styles)
    for tag in soup(["header", "footer", "nav", "script", "style", "noscript"]):
        tag.decompose()

    # First try <main>
    main_tag = soup.find("main")
    if main_tag:
        return main_tag.get_text(separator="\n", strip=True)

    # Then try <article>
    article_tag = soup.find("article")
    if article_tag:
        return article_tag.get_text(separator="\n", strip=True)

    # If no semantic tag, find largest <div>
    divs = soup.find_all("div")
    if divs:
        largest_div = max(divs, key=lambda d: len(d.get_text()))
        return largest_div.get_text(separator="\n", strip=True)

    # Fallback: return entire cleaned body
    return soup.get_text(separator="\n", strip=True)


def split_dom_content(dom_content, max_length=6000):
    return [
        dom_content[i : i + max_length] for i in range(0, len(dom_content), max_length)
    ]


def extract_internal_links(html_content, base_url):
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

