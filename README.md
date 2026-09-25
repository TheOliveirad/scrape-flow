# scrape-flow

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://www.docker.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Async web scraping engine with structured data extraction, built for scale.**

scrape-flow is a production-grade scraping framework that turns URLs into clean, validated data through a composable pipeline architecture. Submit scraping jobs via REST API, let the engine handle concurrency, retries, and rate limiting, and retrieve structured results when they're ready.

---

## Architecture

```
┌──────────────┐       ┌─────────────────────────────────────────────┐
│   Client /   │       │              scrape-flow                    │
│   Webhook    │──────▶│                                             │
└──────────────┘  API  │  ┌─────────┐   ┌──────────┐   ┌─────────┐ │
                       │  │ FastAPI  │──▶│  Engine   │──▶│ Scraper │ │
                       │  │ Routes   │   │          │   │ (async) │ │
                       │  └─────────┘   │ ┌────────┤   └────┬────┘ │
                       │                │ │Semaphor││        │      │
                       │                │ │Rate Lim││   ┌────▼────┐ │
                       │                │ │Retry   ││   │Extractor│ │
                       │                │ └────────┤│   │(Pydantic│ │
                       │                └──────────┘│   └────┬────┘ │
                       │                            │        │      │
                       │                ┌───────────▼────────▼────┐ │
                       │                │     Pipeline Engine     │ │
                       │                │  normalize → validate   │ │
                       │                │  → transform → output   │ │
                       │                └─────────────────────────┘ │
                       └─────────────────────────────────────────────┘
```

## Key Features

- **Async-first engine**: concurrent scraping with configurable semaphore and token-bucket rate limiting
- **Retry with exponential backoff**: automatic retries with jitter to handle transient failures
- **Proxy rotation interface**: pluggable proxy providers (round-robin included, commercial integrations available)
- **Pydantic data models**: every extracted record is validated against a typed schema before output
- **Composable pipelines**: chain transformation steps (normalize, clean, enrich) with per-step telemetry
- **REST API**: submit jobs, check status, and retrieve results via FastAPI endpoints with OpenAPI docs
- **Docker-ready**: multi-stage build with health checks, non-root user, and compose stack included
- **Structured logging**: JSON log output ready for ELK, Datadog, or any log aggregator

## Project Structure

```
scrape-flow/
├── src/
│   ├── main.py                 # FastAPI app factory + lifespan
│   ├── config.py               # Pydantic settings (env-driven)
│   ├── api/
│   │   ├── dependencies.py     # Auth + DI for routes
│   │   └── routes/
│   │       ├── health.py       # /health endpoint
│   │       └── jobs.py         # CRUD for scraping jobs
│   ├── core/
│   │   ├── engine.py           # Async scraping engine
│   │   ├── pipeline.py         # Data pipeline orchestration
│   │   └── scheduler.py        # Job scheduling (interval + one-shot)
│   ├── scrapers/
│   │   ├── base.py             # Abstract BaseScraper interface
│   │   └── example.py          # Demo + skeleton scrapers
│   ├── extractors/
│   │   ├── base.py             # Generic typed extractor
│   │   └── structured.py       # Pydantic schemas + pipeline steps
│   ├── models/
│   │   └── schemas.py          # Shared API schemas
│   └── utils/
│       ├── logging.py          # Structured JSON logger
│       ├── retry.py            # Exponential backoff policy
│       └── proxy.py            # Proxy rotation interface
├── tests/
│   ├── test_engine.py          # Engine lifecycle + job tests
│   ├── test_extractors.py      # Schema + extraction tests
│   └── test_pipeline.py        # Pipeline step + telemetry tests
├── Dockerfile                  # Multi-stage production build
├── docker-compose.yml          # Dev stack (API + Redis)
├── requirements.txt
├── .env.example
└── .gitignore
```

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/TheOliveirad/scrape-flow.git
cd scrape-flow
cp .env.example .env
# Edit .env with your settings
```

### 2. Run with Docker

```bash
docker compose up --build
```

### 3. Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

### 4. Submit a scraping job

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "scraper_name": "product",
    "urls": ["https://jsonplaceholder.typicode.com/posts/1"]
  }'
```

### 5. Check job status

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Use Cases

| Scenario | How scrape-flow helps |
|----------|----------------------|
| **E-commerce price monitoring** | Schedule recurring scrapes, extract product data into validated schemas, export as CSV/JSON |
| **Lead generation** | Scrape directory pages, extract contact info with Pydantic validation, deduplicate via pipeline |
| **Content aggregation** | Pull articles from multiple sources, normalize text, output structured feeds |
| **Market research** | Collect competitor data at scale with proxy rotation and rate limiting |

## Testing

```bash
pytest tests/ -v
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for the full list.

> **Note:** API integrations (proxy providers, storage backends, notification webhooks) use environment variables for credentials. Full production configuration and commercial proxy integration available on request.

## Tech Stack

Python 3.12 · FastAPI · httpx · Pydantic v2 · asyncio · Docker · Redis · pytest

---

## Let's Work Together

I'm a Machine Learning & AI Engineering student specializing in Python automation, async systems, and data pipelines. I build tools that save time and ship production-ready code.

**Looking for a developer who can:**
- Build custom scraping systems that actually scale?
- Design clean APIs and data pipelines?
- Ship Docker-ready automation tools?

**Let's talk:** [Connect on LinkedIn](https://www.linkedin.com/in/diogo-oliveira-python/) | [Hire me on Upwork](https://www.upwork.com/freelancers/~018c8d4a42121d5c16) | [Email me](mailto:oliveira_d@live.com.pt)
