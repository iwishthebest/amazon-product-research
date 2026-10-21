# Detailed Seller Report Implementation Plan

> **For agentic workers:** Execute the tasks inline with test checkpoints.

**Goal:** Upgrade the Amazon AU release report so a small seller can distinguish newness evidence from popularity signals and identify product-improvement opportunities.

**Architecture:** Keep the existing snapshot schema and add pure report-layer scoring and seller guidance. Render a Chinese HTML dashboard with summary metrics, category comparisons, filters, evidence labels, and detailed product cards; do not claim sales without sales/BSR data.

**Tech Stack:** Python standard library, existing pytest suite, standalone HTML/CSS/JavaScript.

## Global Constraints

- `first_seen_at`/`observed_at` means first local observation, not Amazon listing creation time.
- New Releases rank is a popularity signal within the new-release page, not confirmed sales volume.
- Do not add Selenium, captcha bypass, login automation, or unauthorized data sources.
- Keep the existing snapshot/CSV interfaces compatible.

### Task 1: Scoring and evidence helpers

**Files:**
- Modify: `amazon_release/report.py`
- Test: `tests/test_report.py`

- [ ] Add failing tests for rank/review/rating scoring, evidence labels, and improvement advice.
- [ ] Implement pure helpers that return bounded opportunity scores and text guidance.
- [ ] Run focused report tests.

### Task 2: Seller-oriented HTML dashboard

**Files:**
- Modify: `amazon_release/report.py`
- Test: `tests/test_report.py`

- [ ] Add summary cards, category comparison, search/category/hotness filters, and evidence disclaimer.
- [ ] Add product cards containing rank, rating, review count, price, heat signal, competition, and improvement direction.
- [ ] Keep local image paths and safe Amazon links unchanged.
- [ ] Run the full test suite.

### Task 3: Render and verify the current snapshot

**Files:**
- Modify: `README.md`
- Generated: `data/reports/release_2026-10-20.html`

- [ ] Render the existing snapshot with the upgraded report.
- [ ] Verify HTML card counts, local image references, and no unescaped unsafe product data.
- [ ] Run pytest, compileall, and diff checks.
