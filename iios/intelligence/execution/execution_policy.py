"""
iios/intelligence/execution/execution_policy.py
================================================
Execution policies that govern how AI engine calls and workflow steps
are executed within the Intelligence Orchestration Engine.

Policies cover: retry, timeout, fallback, priority, dependency,
resource allocation, load balancing, and cancellation.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..intelligence_constants import (
    PolicyType,
    Priority,
    MAX_RETRY_ATTEMPTS,
    STEP_TIMEOUT_MS,
    WORKFLOW_TIMEOUT_MS,
)

__all__ = [
    "RetryPolicy",
    "TimeoutPolicy",
    "FallbackPolicy",
    "DependencyPolicy",
    "ResourcePolicy",
    "CancellationToken",
    "ExecutionPolicy",
    "DEFAULT_POLICY",
]


@dataclass
class RetryPolicy:
    """Controls retry behaviour for failed steps/engine calls."""
    max_attempts:    int   = MAX_RETRY_ATTEMPTS
    backoff_ms:      float = 500.0      # Initial backoff
    backoff_factor:  float = 2.0        # Exponential multiplier
    max_backoff_ms:  float = 30_000.0   # Cap for backoff
    jitter:          bool  = True       # Add random jitter
    retry_on:        tuple = ()         # Exception types to retry; empty = all

    def should_retry(self, attempt: int, exc: Exception) -> bool:
        if attempt >= self.max_attempts:
            return False
        if self.retry_on and not isinstance(exc, self.retry_on):
            return False
        return True

    def wait_ms(self, attempt: int) -> float:
        """Return wait time in ms before attempt N (0-based)."""
        import random
        ms = min(self.backoff_ms * (self.backoff_factor ** attempt), self.max_backoff_ms)
        if self.jitter:
            ms *= (0.5 + random.random() * 0.5)
        return ms

    def to_dict(self) -> dict:
        return {
            "max_attempts":   self.max_attempts,
            "backoff_ms":     self.backoff_ms,
            "backoff_factor": self.backoff_factor,
            "max_backoff_ms": self.max_backoff_ms,
            "jitter":         self.jitter,
        }


@dataclass
class TimeoutPolicy:
    """Controls timeout behaviour for steps and workflows."""
    step_timeout_ms:     float = STEP_TIMEOUT_MS
    workflow_timeout_ms: float = WORKFLOW_TIMEOUT_MS
    propagate:           bool  = True   # propagate timeout to sub-workflows

    def to_dict(self) -> dict:
        return {
            "step_timeout_ms":     self.step_timeout_ms,
            "workflow_timeout_ms": self.workflow_timeout_ms,
            "propagate":           self.propagate,
        }


@dataclass
class FallbackPolicy:
    """Defines a fallback callable invoked when a step fails."""
    fallback_fn:     Optional[Callable] = None
    fallback_value:  Any               = None
    use_cached:      bool               = False
    silence_errors:  bool               = False

    def apply(self, error: Exception) -> Any:
        if self.silence_errors:
            return self.fallback_value
        if self.fallback_fn is not None:
            return self.fallback_fn(error)
        return self.fallback_value

    def to_dict(self) -> dict:
        return {
            "has_fallback_fn": self.fallback_fn is not None,
            "use_cached":      self.use_cached,
            "silence_errors":  self.silence_errors,
        }


@dataclass
class DependencyPolicy:
    """Controls how step dependencies are resolved."""
    require_all:  bool         = True    # All deps must succeed
    allow_partial: bool        = False   # Allow partially-completed deps
    dep_timeout_ms: float      = WORKFLOW_TIMEOUT_MS

    def to_dict(self) -> dict:
        return {
            "require_all":    self.require_all,
            "allow_partial":  self.allow_partial,
            "dep_timeout_ms": self.dep_timeout_ms,
        }


@dataclass
class ResourcePolicy:
    """Resource limits per workflow execution."""
    max_threads:         int   = 8
    max_memory_mb:       int   = 512
    max_cpu_percent:     float = 80.0
    enable_profiling:    bool  = False
    enable_caching:      bool  = True

    def to_dict(self) -> dict:
        return {
            "max_threads":     self.max_threads,
            "max_memory_mb":   self.max_memory_mb,
            "enable_caching":  self.enable_caching,
            "enable_profiling": self.enable_profiling,
        }


class CancellationToken:
    """
    Thread-safe cancellation signal.

    Steps should check ``token.is_cancelled`` periodically.
    ``token.cancel()`` signals cancellation to all cooperating steps.
    """

    def __init__(self) -> None:
        self._event    = threading.Event()
        self._reason   = ""
        self._ts: Optional[float] = None

    def cancel(self, reason: str = "") -> None:
        self._reason = reason
        self._ts     = time.time()
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str:
        return self._reason

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until cancelled or timeout (seconds). Returns True if cancelled."""
        return self._event.wait(timeout=timeout)

    def reset(self) -> None:
        self._event.clear()
        self._reason = ""
        self._ts     = None


@dataclass
class ExecutionPolicy:
    """
    Aggregated execution policy for a workflow or step.

    Bundles retry, timeout, fallback, dependency, and resource policies
    with a CancellationToken and priority setting.
    """
    priority:     Priority          = Priority.NORMAL
    retry:        RetryPolicy       = field(default_factory=RetryPolicy)
    timeout:      TimeoutPolicy     = field(default_factory=TimeoutPolicy)
    fallback:     FallbackPolicy    = field(default_factory=FallbackPolicy)
    dependency:   DependencyPolicy  = field(default_factory=DependencyPolicy)
    resource:     ResourcePolicy    = field(default_factory=ResourcePolicy)
    cancellation: CancellationToken = field(default_factory=CancellationToken)

    recovery_mode: str = "resume"   # "restart" | "resume" | "skip" | "abort"
    cache_results: bool = True
    enable_tracing: bool = True

    def to_dict(self) -> dict:
        return {
            "priority":      self.priority.name,
            "retry":         self.retry.to_dict(),
            "timeout":       self.timeout.to_dict(),
            "fallback":      self.fallback.to_dict(),
            "dependency":    self.dependency.to_dict(),
            "resource":      self.resource.to_dict(),
            "recovery_mode": self.recovery_mode,
            "cache_results": self.cache_results,
        }


# Shared default policy (immutable-ish — do not mutate shared instances)
DEFAULT_POLICY: ExecutionPolicy = ExecutionPolicy()
