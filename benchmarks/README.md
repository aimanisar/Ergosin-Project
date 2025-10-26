# Benchmarks# Benchmarks



This folder contains a lightweight, reproducible benchmark suite for the Competitive Intelligence Dashboard.This folder contains a lightweight, reproducible benchmark suite for the Competitive Intelligence Dashboard.



What it measures (db scenario):What it measures (db scenario):

- Load cached data from the database (Milvus-backed cache via `storage.load_cache`)- Load cached data from the database (Milvus-backed cache via `storage.load_cache`)

- Chunk text using `TopicSegmentationChunking` (falls back to a simple word-window if unavailable)- Chunk text using `TopicSegmentationChunking` (falls back to a simple word-window if unavailable)

- Fit TF-IDF embeddings on chunks- Fit TF-IDF embeddings on chunks

- Cluster chunk embeddings with KMeans- Cluster chunk embeddings with KMeans



By default, this avoids scraping and LLM calls to keep runs fast and consistent.By default, this avoids scraping and LLM calls to keep runs fast and consistent.



## Quick start (Windows PowerShell)## Quick start (Windows PowerShell)



Run the DB-based benchmark with safe defaults:Run the DB-based benchmark with safe defaults:



```powershell```powershell

python -m benchmarks.benchmark_runner --scenario db --limit 100 --mem --repeat 1python -m benchmarks.benchmark_runner --scenario db --limit 100 --mem --repeat 1

``````



Options:Options:

- `--limit N`       Limit number of pages from the DB to process (default 100)- `--limit N`       Limit number of pages from the DB to process (default 100)

- `--mem`           Track peak memory via tracemalloc- `--mem`           Track peak memory via tracemalloc

- `--repeat R`      Repeat and average timings (default 1)- `--repeat R`      Repeat and average timings (default 1)

- `--profile`       Enable cProfile and write a `.prof` file under `benchmarks/`- `--profile`       Enable cProfile and write a `.prof` file under `benchmarks/`

- `--output path`   Save a JSON report with all metrics- `--output path`   Save a JSON report with all metrics



Examples:Examples:



```powershell```powershell

# Run, track memory, and save JSON report# Run, track memory, and save JSON report

python -m benchmarks.benchmark_runner --scenario db --limit 200 --mem --output benchmarks/report_db.jsonpython -m benchmarks.benchmark_runner --scenario db --limit 200 --mem --output benchmarks/report_db.json



# Run with cProfile and repeat 3 times# Run with cProfile and repeat 3 times

python -m benchmarks.benchmark_runner --scenario db --limit 150 --repeat 3 --profilepython -m benchmarks.benchmark_runner --scenario db --limit 150 --repeat 3 --profile

``````



> Note: The `scrape` and `combined` scenarios are intentionally not implemented in the runner by default, to avoid slow and flaky network/JS-dependent executions during benchmarking. Populate the DB via your normal workflow, then use the `db` scenario for performance analysis.> Note: The `scrape` and `combined` scenarios are intentionally not implemented in the runner by default, to avoid slow and flaky network/JS-dependent executions during benchmarking. Populate the DB via your normal workflow, then use the `db` scenario for performance analysis.



## Output## Output



The console prints a concise timing report like:The console prints a concise timing report like:



``````

=== Benchmark Report ====== Benchmark Report ===

load_cache            0.1234 s, peak=5120 KBload_cache            0.1234 s, peak=5120 KB

chunking              1.4567 s, peak=10240 KBchunking              1.4567 s, peak=10240 KB

tfidf_fit_transform   0.9876 s, peak=20480 KBtfidf_fit_transform   0.9876 s, peak=20480 KB

kmeans_clustering     0.5432 s, peak=4096 KBkmeans_clustering     0.5432 s, peak=4096 KB

``````



If you pass `--output`, a JSON with the same metrics is written to the given path.If you pass `--output`, a JSON with the same metrics is written to the given path.



If you pass `--profile`, a `benchmarks/profile_db.prof` file is generated; you can inspect it with tools like `snakeviz` or `gprof2dot`.If you pass `--profile`, a `benchmarks/profile_db.prof` file is generated; you can inspect it with tools like `snakeviz` or `gprof2dot`.



## Extending## Extending



- To add additional scenarios (e.g., LLM topic generation timing), branch from `benchmark_db` and add a new flow that times `llm_process.call_llm_batch` on a small, representative sample. Keep it opt-in to avoid long runs.- To add additional scenarios (e.g., LLM topic generation timing), branch from `benchmark_db` and add a new flow that times `llm_process.call_llm_batch` on a small, representative sample. Keep it opt-in to avoid long runs.

- To evaluate search performance, time TF-IDF query similarity computations on a fixed set of queries and report QPS/latency percentiles.- To evaluate search performance, time TF-IDF query similarity computations on a fixed set of queries and report QPS/latency percentiles.


