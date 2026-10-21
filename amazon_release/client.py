from __future__ import annotations

import time
from typing import Optional
from urllib.parse import urlparse

import requests


class AmazonFetchError(RuntimeError):
    pass


def validate_amazon_url(url: str, allowed_domain: str = "amazon.com.au") -> str:
    parsed = urlparse(url)
    allowed_hosts = {allowed_domain.lower(), f"www.{allowed_domain.lower()}"}
    if parsed.scheme != "https" or parsed.netloc.lower() not in allowed_hosts:
        raise ValueError(f"Only https://{allowed_domain} URLs are allowed: {url}")
    return url


class AmazonHttpClient:
    def __init__(
        self,
        allowed_domain: str = "amazon.com.au",
        timeout: float = 30.0,
        delay_seconds: float = 1.0,
        max_retries: int = 3,
        user_agent: str = "AmazonReleaseCollector/0.1 (+owner-configured)",
        session: Optional[requests.Session] = None,
    ) -> None:
        self.allowed_domain = allowed_domain
        self.timeout = timeout
        self.delay_seconds = max(0.0, delay_seconds)
        self.max_retries = max(1, max_retries)
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept-Language": "en-AU,en;q=0.9"})
        self._last_request_at = 0.0

    def fetch(self, url: str) -> str:
        validate_amazon_url(url, self.allowed_domain)
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                self._last_request_at = time.monotonic()
                if response.status_code == 200:
                    return response.text
                if response.status_code not in {429, 500, 502, 503, 504}:
                    raise AmazonFetchError(f"HTTP {response.status_code} for {url}")
                last_error = AmazonFetchError(f"HTTP {response.status_code} for {url}")
            except requests.RequestException as exc:
                last_error = exc
            if attempt + 1 < self.max_retries:
                time.sleep(min(30.0, 2**attempt))
        raise AmazonFetchError(f"Failed to fetch {url}: {last_error}") from last_error
