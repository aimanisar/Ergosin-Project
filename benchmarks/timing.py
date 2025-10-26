
#!/usr/bin/env python3
"""
Lightweight timing and profiling helpers for benchmarks.

Provides:
- Timer context manager using perf_counter
- timeit decorator for functions
- optional tracemalloc-based memory tracking
- simple report utilities
"""
from __future__ import annotations

import contextlib
import json
import os
import time
import tracemalloc
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, Optional


@dataclass
class Metrics:
    name: str
    seconds: float
    peak_kb: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Drop None fields for cleanliness
        return {k: v for k, v in d.items() if v is not None}


class Timer:
    """Context manager to measure wall-clock time and optional peak memory."""

    def __init__(self, name: str = "timer", track_memory: bool = False):
        self.name = name
        self.track_memory = track_memory
        self._start: Optional[float] = None
        self._end: Optional[float] = None
        self.seconds: Optional[float] = None
        self.peak_kb: Optional[int] = None

    def __enter__(self):
        if self.track_memory and not tracemalloc.is_tracing():
            tracemalloc.start()
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._end = time.perf_counter()
        self.seconds = (self._end - (self._start or self._end))
        if self.track_memory:
            current, peak = tracemalloc.get_traced_memory()
            self.peak_kb = int(peak / 1024)
            tracemalloc.stop()
        # Do not suppress exceptions
        return False


def timeit(name: Optional[str] = None, track_memory: bool = False):
    """Decorator to time a function call."""

    def _decorator(fn: Callable):
        def _wrapper(*args, **kwargs):
            label = name or fn.__name__
            with Timer(label, track_memory=track_memory) as t:
                result = fn(*args, **kwargs)
            return result, Metrics(name=label, seconds=t.seconds or 0.0, peak_kb=t.peak_kb)

        return _wrapper

    return _decorator


@contextlib.contextmanager
def measure(name: str, track_memory: bool = False):
    t = Timer(name, track_memory=track_memory)
    with t:
        yield t


def print_report(metrics: Dict[str, Metrics]) -> None:
    """Pretty-print a timing report to stdout."""
    if not metrics:
        print("No metrics collected.")
        return
    width = max(len(k) for k in metrics) + 2
    print("\n=== Benchmark Report ===")
    for key, m in metrics.items():
        mem = f", peak={m.peak_kb} KB" if m.peak_kb is not None else ""
        print(f"{key.ljust(width)} {m.seconds:.4f} s{mem}")


def save_report_json(metrics: Dict[str, Metrics], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = {k: v.to_dict() for k, v in metrics.items()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    """Decorator to time a function call."""	"""Decorator to time a function call."""




