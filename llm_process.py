import os, json, time, re, requests

def _get_secret(name, default=None):
    try:
        import streamlit as st
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, default)

OLLAMA_BASE = _get_secret("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = _get_secret("OLLAMA_MODEL", "llama3.2")

MAX_CHARS = 8000
TEMPERATURE = 0.2
TIMEOUT = 120  # seconds

# 🔹 New: Prompt only asks for topics
SYSTEM_PROMPT = (
    "You are a keyword extractor. Given raw webpage text, return ONLY key topics.\n"
    "Always return STRICT JSON array of short phrases (3–6 keywords).\n"
)

USER_PROMPT_TEMPLATE = """\
Extract topics from the following webpage texts.

Return JSON in this form:
[
  {"url": "...", "topics": ["...", "..."]},
  {"url": "...", "topics": ["...", "..."]}
]

TEXTS (truncated):
{pages_text}
"""

def _safe_parse_json(s: str):
    try:
        return json.loads(s)
    except Exception:
        pass
    m = re.search(r"\[.*\]", s, re.DOTALL)  # crude JSON array grab
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return []

def call_llm_batch(pages: list[tuple[str, str]]) -> list[dict]:
    """
    Batch call to LLM: input [(url, text)], return [{"url":..., "topics":[...]}].
    """
    if not pages:
        return []

    # truncate each page text to MAX_CHARS
    text_blocks = []
    for url, text in pages:
        t = (text or "").strip()
        if len(t) > MAX_CHARS:
            t = t[:MAX_CHARS]
        text_blocks.append(f"URL: {url}\nTEXT:\n{t}\n---")

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"<SYSTEM>\n{SYSTEM_PROMPT}\n</SYSTEM>\n\n"
                  f"<USER>\n{USER_PROMPT_TEMPLATE.format(pages_text='\n'.join(text_blocks))}\n</USER>",
        "options": {"temperature": TEMPERATURE},
        "stream": False
    }

    try:
        resp = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("response", "") or ""
        parsed = _safe_parse_json(content)
        print(f"⚡ Using Ollama model: {OLLAMA_MODEL}")
        time.sleep(0.2)
        return parsed
    except Exception as e:
        print("LLM error -> no topics:", e)
        return [{"url": url, "topics": []} for url, _ in pages]

def filter_links_with_llm(urls: list[str], base_url: str) -> list[str]:
    """
    Use LLM to decide which links are relevant to scrape.
    """
    if not urls:
        return []

    prompt = f"""
You are a filtering assistant. I will give you a list of internal URLs from {base_url}.
Return ONLY the URLs that are likely to contain meaningful page content
(such as services, case studies, projects, products, blog, insights).
Exclude utility/boilerplate pages (like careers, jobs, about, team, privacy, cookies, terms, contact).
Return STRICT JSON as:
{{"keep": ["url1", "url2", ...]}}
    
Here are the URLs:
{json.dumps(urls, indent=2)}
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "options": {"temperature": 0.0},
        "stream": False,
    }

    try:
        resp = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("response", "") or "{}"
        parsed = json.loads(content)
        return parsed.get("keep", [])
    except Exception as e:
        print("LLM link filter error -> returning all links:", e)
        return urls
