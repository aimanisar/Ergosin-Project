#!/usr/bin/env python3
"""
Benchmark runner for the Competitive Intelligence Dashboard (clean runner).

Scenarios:
- db: Use existing database/cache to build chunks, TF-IDF embeddings, and clusters.

Options:
--limit N         Limit number of pages/documents used from DB for benchmarking (default: 100)
--profile         Enable cProfile and write stats to benchmarks/profile_*.prof
--mem             Track peak memory via tracemalloc
--repeat R        Repeat the db scenario R times and report averages (default: 1)
--output PATH     Write metrics to JSON file
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from typing import Dict, List

from benchmarks.timing import measure, print_report, Metrics, save_report_json


def _safe_imports():
    try:
        from storage import load_cache
    except Exception as e:
        print("Error importing storage.load_cache:", e)
        raise

    # Optional utilities
    chunker = None
    try:
        from embeddings import TopicSegmentationChunking  # type: ignore
        chunker = TopicSegmentationChunking()
    except Exception:
        chunker = None

    # Vectorization
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    except Exception as e:
        print("scikit-learn not available; please install scikit-learn for embeddings.")
        raise

    # Clustering
    kmeans_cls = None
    try:
        from sklearn.cluster import KMeans  # type: ignore
        kmeans_cls = KMeans
    except Exception:
        kmeans_cls = None

    return load_cache, chunker, TfidfVectorizer, kmeans_cls


def _fallback_chunk(text: str, max_words: int = 200) -> List[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks or ([text] if text else [])


def benchmark_db(limit: int, track_mem: bool, repeat: int) -> Dict[str, Metrics]:
    load_cache, chunker, TfidfVectorizer, KMeansCls = _safe_imports()

    agg_metrics: Dict[str, List[Metrics]] = {}

    for _ in range(repeat):
        metrics: Dict[str, Metrics] = {}

        with measure("load_cache", track_memory=track_mem) as t:
            df = load_cache()
        metrics["load_cache"] = Metrics("load_cache", t.seconds or 0.0, t.peak_kb)

        if df is None or df.empty:
            print("Cache/DB returned no data. Populate the database first.")
            return metrics

        # Select a sample of pages
        sample_df = df.sample(n=min(limit, len(df)), random_state=42) if len(df) > limit else df
        texts: List[str] = [str(x) for x in sample_df.get("content", [])]

        # Chunking
        with measure("chunking", track_memory=track_mem) as t:
            all_chunks: List[str] = []
            for txt in texts:
                if not txt:
                    continue
                if chunker is not None:
                    try:
                        chunks = chunker.chunk(txt)  # type: ignore[attr-defined]
                    except Exception:
                        chunks = _fallback_chunk(txt)
                else:
                    chunks = _fallback_chunk(txt)
                all_chunks.extend(chunks)
        metrics["chunking"] = Metrics("chunking", t.seconds or 0.0, t.peak_kb, extra={"chunks": len(all_chunks)})

        if not all_chunks:
            print("No chunks produced; skipping further steps.")
            return metrics

        # TF-IDF embedding
        with measure("tfidf_fit_transform", track_memory=track_mem) as t:
            vectorizer = TfidfVectorizer(max_features=5000)
            X = vectorizer.fit_transform(all_chunks)
        metrics["tfidf_fit_transform"] = Metrics("tfidf_fit_transform", t.seconds or 0.0, t.peak_kb, extra={"vocab": len(vectorizer.vocabulary_ or {})})

        # Clustering (KMeans) on chunks
        if KMeansCls is not None:
            with measure("kmeans_clustering", track_memory=track_mem) as t:
                n_clusters = max(2, min(10, len(all_chunks) // 50))
                kmeans = KMeansCls(n_clusters=n_clusters, n_init=10, random_state=42)
                kmeans.fit(X)
            metrics["kmeans_clustering"] = Metrics("kmeans_clustering", t.seconds or 0.0, t.peak_kb, extra={"clusters": n_clusters})
        else:
            print("sklearn.cluster.KMeans not available; skipping clustering.")

        # Aggregate across repeats
        for k, m in metrics.items():
            agg_metrics.setdefault(k, []).append(m)

    # Reduce metrics across repeats (average seconds and peak_kb)
    final: Dict[str, Metrics] = {}
    for k, arr in agg_metrics.items():
        avg_sec = sum(m.seconds for m in arr) / len(arr)
        avg_peak = None
        if any(m.peak_kb is not None for m in arr):
            vals = [m.peak_kb or 0 for m in arr]
            avg_peak = int(sum(vals) / len(vals))
        final[k] = Metrics(name=k, seconds=avg_sec, peak_kb=avg_peak, extra=arr[-1].extra)
    return final


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run performance benchmarks")
    parser.add_argument("--scenario", choices=["db"], default="db")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--profile", action="store_true", help="Enable cProfile")
    parser.add_argument("--mem", action="store_true", help="Track peak memory")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--output", type=str, default="", help="Write JSON metrics to this path")
    args = parser.parse_args(argv)

    # Optionally enable cProfile
    if args.profile:
        import cProfile
        prof_path = os.path.join("benchmarks", f"profile_{args.scenario}.prof")
        os.makedirs(os.path.dirname(prof_path), exist_ok=True)
        profiler = cProfile.Profile()
        profiler.enable()
    else:
        profiler = None

    try:
        metrics = benchmark_db(limit=args.limit, track_mem=args.mem, repeat=args.repeat)
    finally:
        if profiler is not None:
            profiler.disable()
            prof_path = os.path.join("benchmarks", f"profile_{args.scenario}.prof")
            profiler.dump_stats(prof_path)
            print(f"cProfile stats written to {prof_path}")

    print_report(metrics)
    if args.output:
        save_report_json(metrics, args.output)
        print(f"Metrics written to {args.output}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
