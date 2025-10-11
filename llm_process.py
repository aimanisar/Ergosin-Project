#!/usr/bin/env python3
"""
LLM Processing Module for Competitive Intelligence Dashboard.

This module handles all AI/LLM interactions including:
- Content summarization and topic extraction
- Competitive analysis using AI
- Link filtering with AI assistance
- Batch processing for efficiency
"""

import os
import json
import time
import re
import requests

def _get_secret(name: str, default=None):
    """Get secret from Streamlit secrets or environment variables."""
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
    "CRITICAL: Return ONLY a valid JSON array. Do not include any explanations, code blocks, or additional text.\n"
    "The response must start with [ and end with ].\n"
    "Format:\n"
    "[\n"
    "  {\"url\": \"...\", \"summary\": \"...\", \"topics\": [\"...\", \"...\", \"...\"]},\n"
    "  ...\n"
    "]\n"
    "Each object must have exactly three fields: \"url\", \"summary\", \"topics\" (where \"topics\" is an array of strings).\n"
    "Rules:\n"
    "- Summary must be concise (2–3 sentences) and in English.\n"
    "- Topics must be 3–6 key phrases (in English).\n"
    "- There are no limits to the number of topics and there must be enough topics to cover all the information in the webpage.\n"
    "- Return ONLY the JSON array, nothing else.\n"
)


USER_PROMPT_TEMPLATE = """\
Summarize and extract key topics from the following webpage texts.  
For each text, if it is not in English, translate it into English before summarizing.

Return ONLY a valid JSON array in this exact format:
[
  {{"url": "...", "summary": "...", "topics": ["...", "...", "...", ...]}},
  ...
]

Do not include any explanations, code blocks, or additional text. Just the JSON array.

TEXTS (truncated):
{pages_text}
"""


def _safe_parse_json(s: str) -> list:
    """Safely parse JSON from LLM response, handling extra text."""
    if not s or not s.strip():
        return []
    
    # Try direct parsing first
    try:
        return json.loads(s.strip())
    except Exception:
        pass
    
    # Try to find JSON array in the response
    start_idx = s.find('[')
    end_idx = s.rfind(']')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = s[start_idx:end_idx + 1]
        try:
            return json.loads(json_str)
        except Exception:
            pass
    
    # Fallback: regex search for JSON array
    match = re.search(r"\[.*\]", s, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    
    return []


def call_llm_batch(pages: list[dict], batch_size: int = 3) -> list[dict]:
    """
    Batch call to LLM: input [{'url':..., 'content':...}],
    return [{'url':..., 'summary':..., 'topics':[...]}].
    Processes pages in smaller chunks to avoid timeouts.
    """
    if not pages:
        return []

    all_results = []

    for i in range(0, len(pages), batch_size):
        batch = pages[i:i + batch_size]
        text_blocks = []
        
        for page in batch:
            url = page.get("url", "")
            text = (page.get("content") or "").strip()
            if len(text) > MAX_CHARS:
                text = text[:MAX_CHARS]
            text_blocks.append(f"URL: {url}\nTEXT:\n{text}\n---")

        joined_blocks='\n'.join(text_blocks)
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": (
                f"<SYSTEM>\n{SYSTEM_PROMPT}\n</SYSTEM>\n\n"
                f"<USER>\n{USER_PROMPT_TEMPLATE.format(pages_text=joined_blocks)}\n</USER>"
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

            # Ensure parsed is always a list of dicts
            if not isinstance(parsed, list):
                parsed = []
            else:
                parsed = [p for p in parsed if isinstance(p, dict)]

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


def call_llm_analysis(analysis_data: dict) -> dict:
    """Use LLM to analyze competitive data and provide intelligent insights."""
    if not analysis_data:
        return {}
    
    prompt = f"""
You are a competitive intelligence analyst. Analyze the following website topic data and provide strategic insights.

BASE WEBSITE: {analysis_data['base_website']}
BASE TOPICS: {', '.join(analysis_data['base_topics'])}

COMPETITOR WEBSITES AND THEIR TOPICS:
{json.dumps(analysis_data['competitors'], indent=2)}

Please analyze this data and return a JSON response with the following structure:

{{
    "trending_topics": {{
        "industry_trends": ["trend1", "trend2", "trend3"],
        "emerging_topics": ["emerging1", "emerging2", "emerging3"],
        "topic_scores": {{"topic1": score1, "topic2": score2}}
    }},
    "competitive_insights": {{
        "strengths": ["strength1", "strength2", "strength3"],
        "opportunities": ["opportunity1", "opportunity2", "opportunity3"],
        "threats": ["threat1", "threat2", "threat3"]
    }},
    "recommendations": [
        {{"title": "Recommendation 1", "description": "Description", "priority": "High"}},
        {{"title": "Recommendation 2", "description": "Description", "priority": "Medium"}}
    ]
}}

Focus on:
1. Identify trending topics across the industry
2. Find emerging topics that competitors are covering but base website isn't
3. Identify competitive strengths and opportunities
4. Provide actionable strategic recommendations

Return ONLY the JSON response, no additional text.
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "options": {"temperature": 0.3},
        "stream": False,
    }

    try:
        resp = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("response", "") or "{}"
        
        parsed = _safe_parse_json(content)
        
        if isinstance(parsed, dict):
            return parsed
        else:
            print("LLM analysis error: Invalid response format")
            return {}
            
    except Exception as e:
        print(f"LLM analysis error: {e}")
        return {}


def filter_links_with_llm(urls: list[str], base_url: str) -> list[str]:
    """Use LLM to decide which links are relevant to scrape."""
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
