# llm_process.py  (Ollama version)
import os, json, time, re, requests

# Config via env or Streamlit secrets (if present)
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

MAX_CHARS = 8000  # keep prompts small to be fast
TEMPERATURE = 0.2
TIMEOUT = 120  # seconds

SYSTEM_PROMPT = (
    "You are a precise content analyst. Given raw webpage text, return a short, useful digest.\n"
    "If the input is mostly cookie banners or navigation, set title='Untitled', "
    "summary='Insufficient content', topics=[].\n"
    "ALWAYS return STRICT JSON with keys: title, summary, topics (list of short phrases)."
)

USER_PROMPT_TEMPLATE = """\
Read the following webpage text and produce a short digest.

Rules:
- Title: <= 8 words.
- Summary: <= 50 words, neutral, factual.
- Topics: 3–5 concise, high-level topics (no hashtags).

Return STRICT JSON:
{{
  "title": "...",
  "summary": "...",
  "topics": ["...", "..."]
}}

TEXT (truncated):
{page_text}
"""

def _fallback(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {"title": "Untitled", "summary": "Insufficient content", "topics": []}
    words = text.split()
    return {
        "title": "Untitled",
        "summary": " ".join(words[:50]),
        "topics": []
    }

def _safe_parse_json(s: str) -> dict:
    # First try direct JSON
    try:
        return json.loads(s)
    except Exception:
        pass
    # Try to extract a JSON block from mixed text
    m = re.search(r"\{(?:[^{}]|(?R))*\}", s, re.DOTALL)  # crude JSON object grab
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}

def call_llm(text: str) -> dict:
    """
    Use a local Ollama model to extract {title, summary, topics[]} from page text.
    """
    text = (text or "").strip()
    if not text:
        return {"title": "Untitled", "summary": "Insufficient content", "topics": []}

    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"<SYSTEM>\n{SYSTEM_PROMPT}\n</SYSTEM>\n\n"
                  f"<USER>\n{USER_PROMPT_TEMPLATE.format(page_text=text)}\n</USER>",
        "options": {"temperature": TEMPERATURE},
        "stream": False
    }

    try:
        resp = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()  # { response: "...", done: true, ... }
        content = data.get("response", "") or ""
        parsed = _safe_parse_json(content)
        title = (parsed.get("title") or "Untitled").strip()
        summary = (parsed.get("summary") or "").strip()
        topics = parsed.get("topics") or []
        print(f"⚡ Using Ollama model: {OLLAMA_MODEL}")
        time.sleep(0.2)  # gentle pacing between pages
        return {"title": title, "summary": summary, "topics": topics}
    except Exception as e:
        print("LLM (Ollama) error -> fallback:", e)
        return _fallback(text)






# # llm_process.py
# import os, json, time

# # Try to read from Streamlit secrets if present
# def _get_secret(name, default=None):
#     try:
#         import streamlit as st  # available when running via streamlit
#         return st.secrets.get(name, default)
#     except Exception:
#         return os.getenv(name, default)

# OPENAI_API_KEY = _get_secret("OPENAI_API_KEY")
# OPENAI_MODEL   = _get_secret("OPENAI_MODEL", "gpt-4o-mini")
# USE_LLM        = bool(OPENAI_API_KEY)

# MAX_CHARS = 8000

# SYSTEM_PROMPT = (
#     "You are a precise content analyst. Given raw webpage text, return a short, useful digest.\n"
#     "If the input is mostly cookie banners or navigation, set title='Untitled', "
#     "summary='Insufficient content', topics=[].\n"
#     "Always return strict JSON with keys: title, summary, topics (list of short phrases)."
# )

# USER_PROMPT_TEMPLATE = """\
# Read the following webpage text and produce a short digest.

# Rules:
# - Title: <= 8 words.
# - Summary: <= 50 words, neutral, factual.
# - Topics: 3–5 concise, high-level topics (no hashtags).

# Return STRICT JSON:
# {{
#   "title": "...",
#   "summary": "...",
#   "topics": ["...", "..."]
# }}

# TEXT (truncated):
# {page_text}
# """

# def _fallback(text: str) -> dict:
#     text = (text or "").strip()
#     if not text:
#         return {"title": "Untitled", "summary": "Insufficient content", "topics": []}
#     first_line = text.splitlines()[0].strip()[:80] or "Untitled"
#     summary = " ".join(text.split()[:50])
#     title = first_line if len(first_line.split()) <= 8 else "Untitled"
#     return {"title": title, "summary": summary, "topics": []}

# def call_llm(text: str) -> dict:
#     text = (text or "").strip()
#     if not text:
#         return {"title": "Untitled", "summary": "Insufficient content", "topics": []}

#     if len(text) > MAX_CHARS:
#         text = text[:MAX_CHARS]

#     if not USE_LLM:
#         print("⚠️  LLM fallback mode (no API key).")
#         return _fallback(text)

#     try:
#         from openai import OpenAI
#         client = OpenAI(api_key=OPENAI_API_KEY)
#         user_prompt = USER_PROMPT_TEMPLATE.format(page_text=text)

#         resp = client.chat.completions.create(
#             model=OPENAI_MODEL,
#             messages=[
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {"role": "user", "content": user_prompt},
#             ],
#             temperature=0.2,
#             response_format={"type": "json_object"},
#         )
#         data = json.loads(resp.choices[0].message.content)
#         print("⚡ Using real LLM:", OPENAI_MODEL)
#         time.sleep(0.25)  # gentle pacing
#         return {
#             "title": (data.get("title") or "Untitled").strip(),
#             "summary": (data.get("summary") or "").strip(),
#             "topics": data.get("topics") or [],
#         }
#     except Exception as e:
#         print("LLM error -> fallback:", e)
#         return _fallback(text)


