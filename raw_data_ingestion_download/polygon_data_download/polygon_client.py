#!/usr/bin/env python3
"""Thin REST client for the Massive.com (Polygon) Stocks API.

Auth is a Bearer token read from POLYGON_API_KEY (or MASSIVE_API_KEY) in the
process environment or the repo .env file. The client handles:
  - exponential backoff on HTTP 429 / 5xx and transient network errors
  - cursor pagination by following the `next_url` field
  - a per-thread requests.Session, so one client instance is safe to share
    across a ThreadPoolExecutor.

The docs don't state a rate limit (Polygon paid tiers are historically
unlimited), so backoff on 429 is the real guard rather than a fixed throttle.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any, Iterator, Optional

import requests

DEFAULT_BASE_URL = "https://api.massive.com"
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
_KEY_NAMES = ("POLYGON_API_KEY", "MASSIVE_API_KEY")


def load_api_key(explicit: Optional[str] = None) -> str:
    """Resolve the API key from (in order) an explicit value, the environment,
    then the repo .env file. Exits with a helpful message if none is found."""
    if explicit:
        return explicit
    for name in _KEY_NAMES:
        v = os.environ.get(name)
        if v:
            return v
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, val = line.partition("=")
            if k.strip() in _KEY_NAMES:
                val = val.strip().strip('"').strip("'")
                if val:
                    return val
    raise SystemExit(
        "No API key found. Set POLYGON_API_KEY in the environment or in "
        f"{ENV_FILE}, or pass --api-key."
    )


class PolygonHTTPError(Exception):
    """Raised for non-retryable HTTP responses (e.g. 404 not-found, 403 plan)."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code


class PolygonClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 30.0,
        max_retries: int = 6,
        throttle: float = 0.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.throttle = throttle
        self._local = threading.local()

    @property
    def _session(self) -> requests.Session:
        """One Session per thread — requests.Session is not guaranteed thread-safe."""
        s = getattr(self._local, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update(
                {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
            )
            self._local.session = s
        return s

    def _url(self, path_or_url: str) -> str:
        if path_or_url.startswith(("http://", "https://")):
            return path_or_url
        return f"{self.base_url}/{path_or_url.lstrip('/')}"

    def get_json(self, path_or_url: str, params: Optional[dict] = None) -> Any:
        """GET and parse JSON, retrying 429/5xx and network errors with backoff.
        Returns the decoded body (dict for wrapped endpoints, list for the bare
        market-holidays endpoint)."""
        url = self._url(path_or_url)
        attempt = 0
        while True:
            attempt += 1
            if self.throttle:
                time.sleep(self.throttle)
            try:
                resp = self._session.get(url, params=params, timeout=self.timeout)
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt > self.max_retries:
                    raise PolygonHTTPError(0, f"network error after {attempt - 1} retries: {e}")
                self._backoff(attempt)
                continue

            sc = resp.status_code
            if sc == 200:
                return resp.json()
            # 403 is retried too: under bulk concurrency Massive intermittently
            # sheds load with an empty-body 403 (the same ticker succeeds on an
            # isolated retry), so treat it as transient and back off rather than
            # dropping the ticker. A genuine plan 403 just exhausts max_retries.
            if sc in (429, 403) or 500 <= sc < 600:
                if attempt > self.max_retries:
                    raise PolygonHTTPError(sc, resp.text[:500])
                self._backoff(attempt, resp.headers.get("Retry-After"))
                continue
            # non-retryable 4xx (404 not-found, 400 bad request, ...)
            raise PolygonHTTPError(sc, resp.text[:500])

    def _backoff(self, attempt: int, retry_after: Optional[str] = None) -> None:
        if retry_after:
            try:
                time.sleep(min(float(retry_after), 60.0))
                return
            except ValueError:
                pass
        time.sleep(min(2.0 ** attempt, 30.0))

    def paginate(
        self, path: str, params: Optional[dict] = None, results_key: str = "results"
    ) -> Iterator[dict]:
        """Yield each item across all pages, following `next_url`. The cursor in
        next_url encodes the original params; auth rides on the Bearer header."""
        payload = self.get_json(path, params)
        while True:
            for item in payload.get(results_key, []) or []:
                yield item
            nxt = payload.get("next_url")
            if not nxt:
                return
            payload = self.get_json(nxt)
