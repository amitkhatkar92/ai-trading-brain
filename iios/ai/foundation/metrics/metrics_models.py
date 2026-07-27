"""
metrics_models.py -- iios.ai.foundation.metrics
================================================
Mutable metric accumulators for the AI Foundation runtime.

Provides RuntimeMetrics, ProviderMetrics, SessionMetrics,
and ExecutionMetrics -- all thread-safe, all observable via
snapshot dicts.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA_VER = "1.0"


# ---------------------------------------------------------------------------
# Rolling latency tracker (helper)
# ---------------------------------------------------------------------------

class _LatencyTracker:
    """Bounded rolling list for latency percentile estimation."""
    _MAX = 1000

    def __init__(self) -> None:
        self._samples: List[float] = []
        self._lock = threading.Lock()

    def record(self, ms: float) -> None:
        with self._lock:
            if len(self._samples) >= self._MAX:
                self._samples.pop(0)
            self._samples.append(ms)

    def avg(self) -> float:
        with self._lock:
            return (sum(self._samples) / len(self._samples)) if self._samples else 0.0

    def p95(self) -> float:
        with self._lock:
            if not self._samples:
                return 0.0
            s = sorted(self._samples)
            idx = max(0, int(len(s) * 0.95) - 1)
            return s[idx]

    def p99(self) -> float:
        with self._lock:
            if not self._samples:
                return 0.0
            s = sorted(self._samples)
            idx = max(0, int(len(s) * 0.99) - 1)
            return s[idx]

    def count(self) -> int:
        with self._lock:
            return len(self._samples)


# ---------------------------------------------------------------------------
# ProviderMetrics
# ---------------------------------------------------------------------------

class ProviderMetrics:
    """Thread-safe metrics for one AI provider."""

    def __init__(self, provider_id: str, model_id: str = "") -> None:
        self.provider_id  = provider_id
        self.model_id     = model_id
        self._lock        = threading.Lock()
        self._requests    = 0
        self._successes   = 0
        self._failures    = 0
        self._timeouts    = 0
        self._total_tokens= 0
        self._latency     = _LatencyTracker()
        self._start       = time.time()

    def record_request(
        self,
        *,
        success:      bool  = True,
        timeout:      bool  = False,
        latency_ms:   float = 0.0,
        total_tokens: int   = 0,
    ) -> None:
        with self._lock:
            self._requests += 1
            if success:
                self._successes += 1
            else:
                self._failures += 1
            if timeout:
                self._timeouts += 1
            self._total_tokens += total_tokens
        self._latency.record(latency_ms)

    def error_rate(self) -> float:
        with self._lock:
            return (self._failures / self._requests) if self._requests else 0.0

    def success_rate(self) -> float:
        with self._lock:
            return (self._successes / self._requests) if self._requests else 0.0

    def throughput_rps(self) -> float:
        with self._lock:
            elapsed = time.time() - self._start
            return (self._requests / elapsed) if elapsed > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            err_rate  = (self._failures  / self._requests) if self._requests else 0.0
            ok_rate   = (self._successes / self._requests) if self._requests else 0.0
            return {
                "provider_id":    self.provider_id,
                "model_id":       self.model_id,
                "requests":       self._requests,
                "successes":      self._successes,
                "failures":       self._failures,
                "timeouts":       self._timeouts,
                "total_tokens":   self._total_tokens,
                "error_rate":     round(err_rate, 4),
                "success_rate":   round(ok_rate,  4),
                "avg_latency_ms": round(self._latency.avg(), 2),
                "p95_latency_ms": round(self._latency.p95(), 2),
                "p99_latency_ms": round(self._latency.p99(), 2),
            }


# ---------------------------------------------------------------------------
# SessionMetrics
# ---------------------------------------------------------------------------

class SessionMetrics:
    """Thread-safe metrics for one AI session."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._lock      = threading.Lock()
        self._requests  = 0
        self._successes = 0
        self._failures  = 0
        self._tokens    = 0
        self._latency   = _LatencyTracker()
        self._created   = time.time()

    def record(self, *, success: bool, latency_ms: float, tokens: int = 0) -> None:
        with self._lock:
            self._requests += 1
            if success:
                self._successes += 1
            else:
                self._failures += 1
            self._tokens += tokens
        self._latency.record(latency_ms)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session_id":     self.session_id,
                "requests":       self._requests,
                "successes":      self._successes,
                "failures":       self._failures,
                "total_tokens":   self._tokens,
                "avg_latency_ms": round(self._latency.avg(), 2),
                "uptime_s":       round(time.time() - self._created, 2),
            }


# ---------------------------------------------------------------------------
# ExecutionMetrics
# ---------------------------------------------------------------------------

class ExecutionMetrics:
    """Metrics for one pipeline execution (created per-request)."""

    def __init__(self, request_id: str) -> None:
        self.request_id  = request_id
        self._stages:    Dict[str, Dict[str, Any]] = {}
        self._lock       = threading.Lock()
        self._start      = time.time()
        self._end:       Optional[float] = None
        self.succeeded:  Optional[bool]  = None
        self.provider_id: str            = ""
        self.total_tokens: int           = 0

    def record_stage(
        self,
        name:       str,
        latency_ms: float,
        succeeded:  bool,
        notes:      str = "",
    ) -> None:
        with self._lock:
            self._stages[name] = {
                "name":       name,
                "latency_ms": round(latency_ms, 2),
                "succeeded":  succeeded,
                "notes":      notes,
            }

    def complete(self, succeeded: bool, provider_id: str = "", total_tokens: int = 0) -> None:
        self._end          = time.time()
        self.succeeded     = succeeded
        self.provider_id   = provider_id
        self.total_tokens  = total_tokens

    def total_latency_ms(self) -> float:
        end = self._end or time.time()
        return (end - self._start) * 1000.0

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "request_id":       self.request_id,
                "total_latency_ms": round(self.total_latency_ms(), 2),
                "succeeded":        self.succeeded,
                "provider_id":      self.provider_id,
                "total_tokens":     self.total_tokens,
                "stages":           dict(self._stages),
            }


# ---------------------------------------------------------------------------
# RuntimeMetrics (platform-wide aggregator)
# ---------------------------------------------------------------------------

class RuntimeMetrics:
    """
    Platform-wide runtime metrics aggregator.

    Holds per-provider metrics and global counters.
    Injected into ExecutionRuntime at startup.
    """

    def __init__(self) -> None:
        self._lock:      threading.Lock              = threading.Lock()
        self._providers: Dict[str, ProviderMetrics]  = {}
        self._total_req  = 0
        self._total_ok   = 0
        self._total_fail = 0
        self._latency    = _LatencyTracker()
        self._start      = time.time()

    def provider_metrics(self, provider_id: str, model_id: str = "") -> ProviderMetrics:
        """Get or create metrics for a provider."""
        with self._lock:
            if provider_id not in self._providers:
                self._providers[provider_id] = ProviderMetrics(provider_id, model_id)
            return self._providers[provider_id]

    def record_execution(self, *, success: bool, latency_ms: float) -> None:
        with self._lock:
            self._total_req += 1
            if success:
                self._total_ok += 1
            else:
                self._total_fail += 1
        self._latency.record(latency_ms)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            providers = {pid: pm.to_dict() for pid, pm in self._providers.items()}
        return {
            "total_requests": self._total_req,
            "total_success":  self._total_ok,
            "total_failure":  self._total_fail,
            "error_rate":     round(
                (self._total_fail / self._total_req) if self._total_req else 0.0, 4
            ),
            "avg_latency_ms": round(self._latency.avg(), 2),
            "p95_latency_ms": round(self._latency.p95(), 2),
            "uptime_s":       round(time.time() - self._start, 2),
            "providers":      providers,
        }
