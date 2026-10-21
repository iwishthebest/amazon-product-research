from __future__ import annotations

import html as html_lib
import json
import re
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import requests


_HIRES_RE = re.compile(r"[\"']hiRes[\"']\s*:\s*[\"'](https?://[^\"']+)[\"']", re.I)


def extract_primary_image_url(page_html: str) -> str | None:
    """Extract the first real product hiRes image from Amazon's colorImages JSON."""
    for match in _HIRES_RE.finditer(page_html):
        candidate = html_lib.unescape(match.group(1)).replace("\\/", "/")
        parsed = urlparse(candidate)
        if parsed.netloc.lower().endswith("media-amazon.com") and "/images/I/" in parsed.path:
            return candidate
    return None


def _image_page_url(asin: str) -> str:
    return f"https://www.amazon.com.au/gp/product/images/{asin}"


def enrich_snapshot_images(
    snapshot_path: str | Path,
    images_dir: str | Path,
    *,
    delay_seconds: float = 0.5,
    timeout_seconds: float = 20.0,
    max_retries: int = 1,
) -> dict[str, int]:
    """Download real Amazon hiRes images and update snapshot image_url to local paths."""
    snapshot = Path(snapshot_path)
    images = Path(images_dir)
    images.mkdir(parents=True, exist_ok=True)
    records = json.loads(snapshot.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers.update({"User-Agent": "AmazonReleaseCollector/0.1 (+owner-configured)", "Accept-Language": "en-AU,en;q=0.9"})
    downloaded = 0
    skipped = 0
    failed = 0
    for record in records:
        asin = str(record.get("asin", "")).strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{10}", asin):
            failed += 1
            continue
        target = images / f"{asin}.jpg"
        if target.exists() and target.stat().st_size > 1000:
            record["image_url"] = f"images/{asin}.jpg"
            skipped += 1
            continue
        image_url = None
        for attempt in range(max(1, max_retries)):
            try:
                page = session.get(_image_page_url(asin), timeout=timeout_seconds)
                if page.status_code == 200:
                    image_url = extract_primary_image_url(page.text)
                if image_url:
                    image = session.get(image_url, timeout=timeout_seconds)
                    content_type = image.headers.get("Content-Type", "")
                    if image.status_code == 200 and content_type.startswith("image/") and len(image.content) > 1000:
                        target.write_bytes(image.content)
                        record["image_url"] = f"images/{asin}.jpg"
                        downloaded += 1
                        break
            except requests.RequestException:
                pass
            if attempt + 1 < max(1, max_retries):
                time.sleep(2**attempt)
        else:
            failed += 1
        if delay_seconds:
            time.sleep(delay_seconds)
    temp = snapshot.with_suffix(snapshot.suffix + ".tmp")
    temp.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(snapshot)
    return {"downloaded": downloaded, "skipped": skipped, "failed": failed, "total": len(records)}
