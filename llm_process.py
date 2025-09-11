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

MAX_CHARS = 3000
TEMPERATURE = 0.2
TIMEOUT = 300  # seconds

SYSTEM_PROMPT = (
    "You are a summarizer and keyword extractor. "
    "Given raw webpage text, return BOTH:\n"
    "1. A concise summary (2–3 sentences).\n"
    "2. Key topics (3–6 keywords).\n"
    "Always return STRICT JSON with 'url', 'summary', and 'topics'."
)

USER_PROMPT_TEMPLATE = """\
Extract a short summary and key topics from the following webpage texts.

Return JSON in this form:
[
  {{"url": "...", "summary": "short summary...", "topics": ["...", "..."]}},
  {{"url": "...", "summary": "short summary...", "topics": ["...", "..."]}}
]

TEXTS (truncated):
{pages_text}
"""



def _safe_parse_json(s: str):
    try:
        data = json.loads(s)
        return data if isinstance(data, list) else []
    except Exception:
        m = re.search(r"\[.*\]", s, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except:
                pass
    return []


def call_llm_batch(pages: list[dict], batch_size: int = 5) -> list[dict]:
    """
    Batch call to LLM safely:
    - Input: [{"url":..., "content":...}]
    - Output: [{"url":..., "summary":..., "topics":[...]}]
    """
    if not pages:
        return []

    results = []

    # process in smaller groups
    for i in range(0, len(pages), batch_size):
        batch = pages[i:i + batch_size]

        text_blocks = []
        for page in batch:
            url = page["url"]
            text = (page["content"] or "").strip()
            if len(text) > MAX_CHARS:
                text = text[:MAX_CHARS]
            # clean up text aggressively
            text = text.replace("\n", " ").replace("\r", " ")
            text_blocks.append(f"URL: {url}\nTEXT:\n{text}\n---")

        prompt = (
            f"<SYSTEM>\n{SYSTEM_PROMPT}\n</SYSTEM>\n\n"
            f"<USER>\n{USER_PROMPT_TEMPLATE.format(pages_text='\n'.join(text_blocks))}\n</USER>"
        )

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "options": {"temperature": TEMPERATURE},
            "stream": False
        }

        # retry logic
        for attempt in range(3):
            try:
                resp = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                content = data.get("response", "") or ""
                print("RAW LLM OUTPUT:", content[:500])
                parsed = _safe_parse_json(content)

                # make sure we always get url + summary + topics
                for page in batch:
                    url = page["url"]
                    match = next((r for r in parsed if r.get("url") == url), None)
                    if match:
                        results.append({
                            "url": url,
                            "summary": match.get("summary", ""),
                            "topics": match.get("topics", [])
                        })
                    else:
                        results.append({"url": url, "summary": "", "topics": []})

                print(f"⚡ Batch {i//batch_size+1}: processed {len(batch)} pages")
                time.sleep(0.2)
                break  # success → stop retry loop

            except Exception as e:
                print(f"LLM error (attempt {attempt+1}) on batch {i//batch_size+1}:", e)
                if attempt == 2:  # last try failed
                    for page in batch:
                        results.append({"url": page["url"], "summary": "", "topics": []})

    return results


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
