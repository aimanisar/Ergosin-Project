from typing import List, Dict, Tuple, Any, Iterable
import logging
from bs4 import BeautifulSoup

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Optional NLTK text-tiling tokenizer (fallback to paragraph/window chunking)
try:
    from nltk.tokenize import TextTilingTokenizer
    _HAS_TEXTTILING = True
except Exception:
    TextTilingTokenizer = None
    _HAS_TEXTTILING = False


class TopicSegmentationChunking:
    """Chunk document text into topical chunks. Uses NLTK TextTiling if available, else paragraph/window fallback."""

    def __init__(self, window_words: int = 200):
        self.window_words = window_words
        if _HAS_TEXTTILING and TextTilingTokenizer is not None:
            try:
                self.tokenizer = TextTilingTokenizer()
            except Exception:
                logging.warning("TextTilingTokenizer failed to init; falling back.")
                self.tokenizer = None
        else:
            self.tokenizer = None

    def _preprocess_text(self, text: str) -> str:
        # If HTML-like content or no paragraph breaks, convert with BeautifulSoup using paragraph separators.
        txt = text or ""
        if ("<" in txt and ">" in txt) or ("\n\n" not in txt and len(txt.split()) > 50):
            try:
                soup = BeautifulSoup(txt, "html.parser")
                # use double-newline as paragraph separator
                txt = soup.get_text(separator="\n\n")
            except Exception:
                logging.exception("BeautifulSoup preprocessing failed; continuing with raw text.")
        # normalize newlines and whitespace
        txt = txt.replace("\r\n", "\n").replace("\r", "\n")
        # collapse repeated newlines to at most two
        while "\n\n\n" in txt:
            txt = txt.replace("\n\n\n", "\n\n")
        txt = "\n\n".join(part.strip() for part in txt.split("\n\n") if part.strip())
        return txt

    def chunk(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []
        text = self._preprocess_text(text)

        # prepare paragraph list and basic stats
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        total_words = sum(len(p.split()) for p in paras)

        # Only attempt TextTiling if tokenizer exists AND text looks suitable:
        # require at least 3 paragraphs and a modest word count
        if self.tokenizer and len(paras) >= 3 and total_words >= max(self.window_words, 100):
            try:
                tiles = [c.strip() for c in self.tokenizer.tokenize(text) if c.strip()]
                if tiles:
                    return tiles
            except Exception:
                logging.exception("TextTiling failed; falling back.")

        # fallback: split by paragraphs and group into windows of ~window_words
        # (re-use paras computed above)
        chunks = []
        cur = []
        cur_words = 0
        for p in paras:
            cur.append(p)
            cur_words += len(p.split())
            if cur_words >= self.window_words:
                chunks.append(" ".join(cur))
                cur = []
                cur_words = 0
        if cur:
            chunks.append(" ".join(cur))
        return chunks


class GlobalSearchEngine:
    """
    Build a TF-IDF index over chunks extracted from website pages and run cosine-similarity search.

    Usage:
      engine = GlobalSearchEngine()
      engine.build_index_from_rows(rows)   # rows = iterable of dicts with keys 'page_url','page_name','content'
      results = engine.query("your query", top_k=10)
    """

    def __init__(self, max_features: int = 20000, stop_words: str = "english"):
        self.chunker = TopicSegmentationChunking()
        self.vectorizer = TfidfVectorizer(max_features=max_features, stop_words=stop_words)
        self._matrix = None                # TF-IDF matrix for chunks
        self._meta: List[Dict[str, Any]] = []  # metadata per chunk: {url, page_name, chunk_text, chunk_idx}
        self._fitted = False

    def build_index_from_rows(self, rows: Iterable[Dict[str, Any]]) -> None:
        """Accept rows as iterable of dict-like objects with keys 'page_url','page_name','content'."""
        chunks = []
        meta = []
        idx = 0
        for r in rows:
            url = r.get("page_url", "") or ""
            page_name = r.get("page_name") or url
            content = (r.get("content") or "").strip()
            if not content:
                continue
            piece_chunks = self.chunker.chunk(content) or [content[:1000]]
            for c in piece_chunks:
                chunks.append(c)
                meta.append({"url": url, "page_name": page_name, "chunk_text": c, "chunk_idx": idx})
                idx += 1

        if not chunks:
            self._matrix = None
            self._meta = []
            self._fitted = False
            return

        self._matrix = self.vectorizer.fit_transform(chunks)
        self._meta = meta
        self._fitted = True

    def build_index_from_dataframe(self, df) -> None:
        """DataFrame-friendly wrapper (pandas.DataFrame expected with cols page_url,page_name,content)."""
        try:
            rows = df.to_dict(orient="records")
        except Exception:
            rows = list(df)
        self.build_index_from_rows(rows)

    def query(self, q: str, top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """Return list of (metadata, score) sorted by score desc. Metadata: url,page_name,chunk_text,chunk_idx."""
        if not self._fitted or self._matrix is None or not q or not q.strip():
            return []
        qv = self.vectorizer.transform([q])
        sims = cosine_similarity(qv, self._matrix).flatten()
        top_idx = np.argsort(-sims)[:top_k]
        return [(self._meta[i], float(sims[i])) for i in top_idx if sims[i] > 0]

    def query_aggregate_pages(self, q: str, top_k_pages: int = 10) -> List[Tuple[str, float]]:
        """Aggregate chunk scores per page (use max chunk score as page score) and return top pages."""
        hits = self.query(q, top_k=5000)
        scores_by_url = {}
        for meta, score in hits:
            url = meta["url"]
            scores_by_url.setdefault(url, []).append(score)
        aggregated = [(url, max(scores)) for url, scores in scores_by_url.items()]
        aggregated.sort(key=lambda x: x[1], reverse=True)
        return aggregated[:top_k_pages]