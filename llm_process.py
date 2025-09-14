# llm_process.py
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

MAX_CHARS = 2000
TEMPERATURE = 0.2
TIMEOUT = 500  # seconds

# 🔹 Prompt now asks for topics AND summary
SYSTEM_PROMPT = (
    "You are a text summarizer and topic extractor.\n"
    "Given raw webpage text (which may be in any language), produce both a concise summary and key topics in English.\n"
    "If the content is not in English, translate it into English before summarizing or extracting topics.\n"
    "Always return a STRICT JSON array of objects with the following format:\n"
    "[\n"
    "  {\"url\": \"...\", \"summary\": \"...\", \"topics\": [\"...\", \"...\", \"...\"]},\n"
    "  ...\n"
    "]\n"
    "Each object must have exactly three fields: \"url\", \"summary\", \"topics\" (where \"topics\" is an array of strings).\n"
    "Rules:\n"
    "- Summary must be concise (2–3 sentences) and in English.\n"
    "- Topics must be 3–6 key phrases (in English).\n"
)


USER_PROMPT_TEMPLATE = """\
Summarize and extract key topics from the following webpage texts.  
For each text, if it is not in English, translate it into English before summarizing.

Return JSON in this form:
[
  {{"url": "...", "summary": "...", "topics": ["...", "...", "..."]}},
  ...
]

TEXTS (truncated):
{pages_text}
"""


def _safe_parse_json(s: str):
    try:
        return json.loads(s)
    except Exception:
        pass
    # crude attempt to grab JSON array
    m = re.search(r"\[.*\]", s, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return []

# def call_llm_batch(pages: list[dict]) -> list[dict]:
#     """
#     Batch call to LLM: input [{'url':..., 'content':...}],
#     return [{'url':..., 'topics': [...], 'summary': "..."}].
#     """
#     if not pages:
#         return []

#     text_blocks = []
#     for page in pages:
#         url = page.get("url", "")
#         text = (page.get("content") or "").strip()
#         if len(text) > MAX_CHARS:
#             text = text[:MAX_CHARS]
#         text_blocks.append(f"URL: {url}\nTEXT:\n{text}\n---")

#     payload = {
#         "model": OLLAMA_MODEL,
#         "prompt": (
#             f"<SYSTEM>\n{SYSTEM_PROMPT}\n</SYSTEM>\n\n"
#             f"<USER>\n{USER_PROMPT_TEMPLATE.format(pages_text='\n'.join(text_blocks))}\n</USER>"
#         ),
#         "options": {"temperature": TEMPERATURE},
#         "stream": False,
#     }

#     try:
#         resp = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=TIMEOUT)
#         resp.raise_for_status()
#         data = resp.json()
#         content = data.get("response", "") or ""
#         parsed = _safe_parse_json(content)

#         # Ensure consistent shape
#         results = []
#         for page in pages:
#             url = page["url"]
#             match = next((p for p in parsed if p.get("url") == url), None)
#             if match:
#                 results.append({
#                     "url": url,
#                     "topics": match.get("topics", []),
#                     "summary": match.get("summary", "")
#                 })
#             else:
#                 results.append({"url": url, "topics": [], "summary": ""})
#         return results

#     except Exception as e:
#         print("LLM error -> no topics:", e)
#         return [{"url": p["url"], "topics": [], "summary": ""} for p in pages]

def call_llm_batch(pages: list[dict], batch_size: int = 3) -> list[dict]:
    """
    Batch call to LLM: input [{'url':..., 'content':...}],
    return [{'url':..., 'summary':..., 'topics':[...]}].
    Processes pages in smaller chunks to avoid timeouts.
    """
    if not pages:
        return []

    all_results = []

    # Split pages into batches
    for i in range(0, len(pages), batch_size):
        batch = pages[i:i + batch_size]
        text_blocks = []
        for page in batch:
            url = page.get("url", "")
            text = (page.get("content") or "").strip()
            if len(text) > MAX_CHARS:
                text = text[:MAX_CHARS]
            text_blocks.append(f"URL: {url}\nTEXT:\n{text}\n---")

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": (
                f"<SYSTEM>\n{SYSTEM_PROMPT}\n</SYSTEM>\n\n"
                f"<USER>\n{USER_PROMPT_TEMPLATE.format(pages_text='\n'.join(text_blocks))}\n</USER>"
            ),
            "options": {"temperature": TEMPERATURE},
            "stream": False,
        }

        try:
            resp = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("response", "") or ""
            parsed = _safe_parse_json(content)

            # Match results back to URLs in this batch
            for page in batch:
                url = page["url"]
                match = next((p for p in parsed if p.get("url") == url), None)
                if match:
                    all_results.append({
                        "url": url,
                        "summary": match.get("summary", ""),
                        "topics": match.get("topics", [])
                    })
                else:
                    all_results.append({"url": url, "summary": "", "topics": []})

        except Exception as e:
            print(f"⚠️ LLM error in batch {i//batch_size+1}: {e}")
            for page in batch:
                all_results.append({"url": page["url"], "summary": "", "topics": []})

        time.sleep(0.3)  # small pause between batches

    return all_results



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


# print("🔎 Raw LLM response:", content[:500])  # first 500 chars
























# import os, json, time, re, requests

# def _get_secret(name, default=None):
#     try:
#         import streamlit as st
#         if name in st.secrets:
#             return st.secrets[name]
#     except Exception:
#         pass
#     return os.getenv(name, default)

# OLLAMA_BASE = _get_secret("OLLAMA_BASE_URL", "http://localhost:11434")
# OLLAMA_MODEL = _get_secret("OLLAMA_MODEL", "llama3.2")

# MAX_CHARS = 3000
# TEMPERATURE = 0.2
# TIMEOUT = 300  # seconds

# SYSTEM_PROMPT = (
#     "You are a summarizer and keyword extractor. "
#     "Given raw webpage text, return BOTH:\n"
#     "1. A concise summary (2–3 sentences).\n"
#     "2. Key topics (3–6 keywords).\n"
#     "Always return STRICT JSON with 'url', 'summary', and 'topics'."
# )

# USER_PROMPT_TEMPLATE = """\
# Extract a short summary and key topics from the following webpage texts.

# Return JSON in this form:
# [
#   {{"url": "...", "summary": "short summary...", "topics": ["...", "..."]}},
#   {{"url": "...", "summary": "short summary...", "topics": ["...", "..."]}}
# ]

# TEXTS (truncated):
# {pages_text}
# """



# def _safe_parse_json(s: str):
#     try:
#         data = json.loads(s)
#         return data if isinstance(data, list) else []
#     except Exception:
#         m = re.search(r"\[.*\]", s, re.DOTALL)
#         if m:
#             try:
#                 return json.loads(m.group(0))
#             except:
#                 pass
#     return []


# def call_llm_batch(pages: list[dict], batch_size: int = 5) -> list[dict]:
#     """
#     Batch call to LLM safely:
#     - Input: [{"url":..., "content":...}]
#     - Output: [{"url":..., "summary":..., "topics":[...]}]
#     """
#     if not pages:
#         return []

#     results = []

#     # process in smaller groups
#     for i in range(0, len(pages), batch_size):
#         batch = pages[i:i + batch_size]

#         text_blocks = []
#         for page in batch:
#             url = page["url"]
#             text = (page["content"] or "").strip()
#             if len(text) > MAX_CHARS:
#                 text = text[:MAX_CHARS]
#             # clean up text aggressively
#             text = text.replace("\n", " ").replace("\r", " ")
#             text_blocks.append(f"URL: {url}\nTEXT:\n{text}\n---")

#         prompt = (
#             f"<SYSTEM>\n{SYSTEM_PROMPT}\n</SYSTEM>\n\n"
#             f"<USER>\n{USER_PROMPT_TEMPLATE.format(pages_text='\n'.join(text_blocks))}\n</USER>"
#         )

#         payload = {
#             "model": OLLAMA_MODEL,
#             "prompt": prompt,
#             "options": {"temperature": TEMPERATURE},
#             "stream": False
#         }

#         # retry logic
#         for attempt in range(3):
#             try:
#                 resp = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=TIMEOUT)
#                 resp.raise_for_status()
#                 data = resp.json()
#                 content = data.get("response", "") or ""
#                 print("RAW LLM OUTPUT:", content[:500])
#                 parsed = _safe_parse_json(content)

#                 # make sure we always get url + summary + topics
#                 for page in batch:
#                     url = page["url"]
#                     match = next((r for r in parsed if r.get("url") == url), None)
#                     if match:
#                         results.append({
#                             "url": url,
#                             "summary": match.get("summary", ""),
#                             "topics": match.get("topics", [])
#                         })
#                     else:
#                         results.append({"url": url, "summary": "", "topics": []})

#                 print(f"⚡ Batch {i//batch_size+1}: processed {len(batch)} pages")
#                 time.sleep(0.2)
#                 break  # success → stop retry loop

#             except Exception as e:
#                 print(f"LLM error (attempt {attempt+1}) on batch {i//batch_size+1}:", e)
#                 if attempt == 2:  # last try failed
#                     for page in batch:
#                         results.append({"url": page["url"], "summary": "", "topics": []})

#     return results


# def filter_links_with_llm(urls: list[str], base_url: str) -> list[str]:
#     """
#     Use LLM to decide which links are relevant to scrape.
#     """
#     if not urls:
#         return []

#     prompt = f"""
# You are a filtering assistant. I will give you a list of internal URLs from {base_url}.
# Return ONLY the URLs that are likely to contain meaningful page content
# (such as services, case studies, projects, products, blog, insights).
# Exclude utility/boilerplate pages (like careers, jobs, about, team, privacy, cookies, terms, contact).
# Return STRICT JSON as:
# {{"keep": ["url1", "url2", ...]}}

# Here are the URLs:
# {json.dumps(urls, indent=2)}
# """

#     payload = {
#         "model": OLLAMA_MODEL,
#         "prompt": prompt,
#         "options": {"temperature": 0.0},
#         "stream": False,
#     }

#     try:
#         resp = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=TIMEOUT)
#         resp.raise_for_status()
#         data = resp.json()
#         content = data.get("response", "") or "{}"
#         parsed = json.loads(content)
#         return parsed.get("keep", [])
#     except Exception as e:
#         print("LLM link filter error -> returning all links:", e)
#         return urls
