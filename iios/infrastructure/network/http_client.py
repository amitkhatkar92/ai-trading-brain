"""
iios/infrastructure/network/http_client.py
==========================================
HTTP client with retry and circuit-breaker integration.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from ..infrastructure_constants import DEFAULT_HTTP_TIMEOUT_SECONDS, DEFAULT_RETRY_ATTEMPTS
from ..infrastructure_exceptions import NetworkError
from ..infrastructure_models import HttpRequest, HttpResponse
from ..utilities.circuit_breaker import CircuitBreaker
from ..utilities.retry import RetryConfig

__all__ = ["HttpClient"]

_LOG = logging.getLogger("iios.infrastructure.network.http_client")


class HttpClient:
    """Simple HTTP client built on Python's stdlib urllib.

    Supports GET/POST/PUT/DELETE with automatic retry and circuit-breaker.

    Usage::

        client = HttpClient(base_url="https://api.dhan.co", timeout=10)
        response = client.get("/v2/orders", headers={"Authorization": "Bearer TOKEN"})
        data = response.json()
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_RETRY_ATTEMPTS,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retry_config = RetryConfig(
            max_attempts=max_retries,
            exceptions=(urllib.error.URLError, ConnectionError, TimeoutError),
        )
        self._circuit = CircuitBreaker(
            name=f"http_{base_url[:30]}",
            threshold=circuit_breaker_threshold,
            reset_timeout=circuit_breaker_timeout,
        )
        self._default_headers: dict[str, str] = {
            "User-Agent": "IIOS/1.0",
            "Accept": "application/json",
        }

    def get(self, path: str, *, headers: Optional[dict] = None, params: Optional[dict] = None) -> HttpResponse:
        return self._request("GET", path, headers=headers, params=params)

    def post(self, path: str, *, body: Any = None, headers: Optional[dict] = None) -> HttpResponse:
        return self._request("POST", path, body=body, headers=headers)

    def put(self, path: str, *, body: Any = None, headers: Optional[dict] = None) -> HttpResponse:
        return self._request("PUT", path, body=body, headers=headers)

    def delete(self, path: str, *, headers: Optional[dict] = None) -> HttpResponse:
        return self._request("DELETE", path, headers=headers)

    def set_default_header(self, key: str, value: str) -> None:
        self._default_headers[key] = value

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: Any = None,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> HttpResponse:
        url = self._build_url(path, params)
        merged_headers = dict(self._default_headers)
        if headers:
            merged_headers.update(headers)

        body_bytes: Optional[bytes] = None
        if body is not None:
            if isinstance(body, (dict, list)):
                body_bytes = json.dumps(body).encode("utf-8")
                merged_headers.setdefault("Content-Type", "application/json")
            elif isinstance(body, str):
                body_bytes = body.encode("utf-8")
            elif isinstance(body, bytes):
                body_bytes = body

        req = urllib.request.Request(url, data=body_bytes, headers=merged_headers, method=method)
        t_start = time.monotonic()

        def _execute() -> HttpResponse:
            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    duration_ms = (time.monotonic() - t_start) * 1000
                    resp_headers = dict(resp.headers)
                    resp_body = resp.read()
                    return HttpResponse(
                        status_code=resp.status,
                        body=resp_body,
                        headers=resp_headers,
                        duration_ms=duration_ms,
                        url=url,
                    )
            except urllib.error.HTTPError as exc:
                duration_ms = (time.monotonic() - t_start) * 1000
                resp_body = exc.read() if exc.fp else b""
                return HttpResponse(
                    status_code=exc.code,
                    body=resp_body,
                    headers={},
                    duration_ms=duration_ms,
                    url=url,
                )
            except urllib.error.URLError as exc:
                raise NetworkError(
                    f"HTTP {method} {url} failed: {exc.reason}",
                    code="INF-NET-001",
                    context={"url": url, "method": method},
                ) from exc

        for attempt in range(self._retry_config.max_attempts):
            try:
                return self._circuit.call(_execute)
            except NetworkError:
                if attempt == self._retry_config.max_attempts - 1:
                    raise
                delay = self._retry_config.backoff_for(attempt)
                _LOG.warning("HTTP %s %s attempt %d failed — retrying in %.2fs",
                             method, url, attempt + 1, delay)
                time.sleep(delay)

        raise NetworkError(f"HTTP {method} {url} exhausted all retries", code="INF-NET-002")

    def _build_url(self, path: str, params: Optional[dict] = None) -> str:
        base = self._base_url + ("/" + path.lstrip("/") if path else "")
        if params:
            query = urllib.parse.urlencode(params)
            base = f"{base}?{query}"
        return base
