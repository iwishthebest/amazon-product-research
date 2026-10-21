# Amazon AU New Releases Collector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable Python CLI that discovers Pilates/Yoga subcategories on Amazon Australia New Releases pages, follows pagination, extracts product cards, persists daily snapshots, and exports newly observed ASINs.

**Architecture:** Keep network access behind an injectable fetcher so parser, pagination, category discovery, and persistence are testable offline. Use BeautifulSoup for HTML parsing, SQLite for durable state, JSON for raw page snapshots, and CSV for daily reports. The CLI supports a dry-run fixture mode and a live mode with explicit rate limiting/retries.

**Tech Stack:** Python 3.11+, `requests`, `beautifulsoup4`, `pytest`, SQLite, argparse.

## Global Constraints

- Default marketplace is Australia (`A39IBJ37TRP1C6`) and all URLs must remain under `amazon.com.au` unless explicitly configured.
- Newness means first observed by this collector; it must not be labeled as Amazon's actual listing creation timestamp.
- No CAPTCHA/login bypass, aggressive concurrency, or hidden scraping behavior.
- Tests must not call Amazon; fixtures must cover category discovery, pagination, product extraction, deduplication, and daily diffing.

### Task 1: Project scaffolding and parser contracts

**Files:**
- Create: `amazon_release/__init__.py`
- Create: `amazon_release/models.py`
- Create: `amazon_release/parser.py`
- Test: `tests/test_parser.py`

- [ ] Write failing tests for extracting category links, product cards, and next-page URLs from representative HTML fixtures.
- [ ] Run `pytest tests/test_parser.py -q` and confirm failure because modules/functions do not exist.
- [ ] Implement typed dataclasses and BeautifulSoup parser functions.
- [ ] Run the parser tests and confirm green.

### Task 2: HTTP client and crawl orchestration

**Files:**
- Create: `amazon_release/client.py`
- Create: `amazon_release/crawler.py`
- Test: `tests/test_crawler.py`

- [ ] Write failing tests for domain validation, retryable status handling, category traversal, pagination, and ASIN deduplication using an in-memory fetcher.
- [ ] Run the focused tests and confirm expected failures.
- [ ] Implement the bounded `requests.Session` client and crawler.
- [ ] Run focused tests and confirm green.

### Task 3: SQLite persistence and report export

**Files:**
- Create: `amazon_release/storage.py`
- Test: `tests/test_storage.py`

- [ ] Write failing tests for first-seen semantics, repeat observations, and CSV export.
- [ ] Run focused tests and confirm failure.
- [ ] Implement SQLite schema, upsert/diff logic, and CSV export.
- [ ] Run focused tests and confirm green.

### Task 4: CLI, configuration, fixtures, and documentation

**Files:**
- Create: `amazon_release/cli.py`
- Create: `run_amazon_release.py`
- Create: `config.example.json`
- Create: `requirements.txt`
- Create: `tests/fixtures/*.html`
- Create: `README.md`
- Test: `tests/test_cli.py`

- [ ] Write failing CLI test for fixture mode and generated report.
- [ ] Run focused test and confirm failure.
- [ ] Implement CLI options for `--config`, `--fixture-dir`, `--db`, `--output-dir`, `--dry-run`, and `--delay-seconds`.
- [ ] Run the full suite, a fixture-mode smoke run, and `python run_amazon_release.py --help`.
- [ ] Update README with Amazon policy boundary, scheduling example, and interpretation of `first_seen_at`.
