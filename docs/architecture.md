# Architecture Overview

## Design Principles

1. **Interface-driven** — core abstractions (`BaseScraper`, `BaseExtractor`, `ProxyProvider`) allow swapping implementations without touching engine code
2. **Async-first** — all I/O is non-blocking via `asyncio` and `httpx`, enabling high throughput on a single process
3. **Fail gracefully** — exponential backoff with jitter, per-URL error isolation, and pipeline short-circuiting ensure partial failures don't crash the system
4. **Observable** — structured JSON logging and per-step pipeline telemetry make debugging straightforward

## Request Flow

```
POST /api/v1/jobs
    │
    ▼
JobCreateRequest (Pydantic validation)
    │
    ▼
ScrapeEngine.submit()
    ├── Creates ScrapeJob
    ├── Spawns async task
    │
    ▼
_process_job()
    ├── For each URL:
    │   ├── Semaphore.acquire()
    │   ├── RateLimiter.acquire()
    │   ├── Scraper.fetch(url)
    │   ├── Scraper.extract(raw)
    │   └── Retry on failure (exponential backoff)
    │
    ▼
Job.results populated
Job.status → COMPLETED | FAILED
```

## Extension Points

| Component | Interface | Purpose |
|-----------|-----------|---------|
| Scrapers | `BaseScraper` | Add new site-specific scrapers |
| Extractors | `BaseExtractor[T]` | Custom typed data extraction |
| Proxy providers | `ProxyProvider` | Plug in commercial proxy services |
| Pipeline steps | `async (Any) → Any` | Add transformation/enrichment steps |
| Storage | `DATABASE_URL` env var | Swap SQLite for PostgreSQL, etc. |
