"""
portfolio_integration_statistics.py — iios.portfolio.integration
=================================================================
Thread-safe statistics accumulator for the Portfolio Integration subsystem.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from typing import Any, Dict


class PortfolioIntegrationStatistics:
    """
    Thread-safe statistics accumulator for the integration engine.

    Counters
    --------
    portfolio_requests :      Total requests submitted.
    portfolio_sessions :      Total lifecycle sessions created.
    snapshots_published :     Total snapshots published.
    portfolio_optimizations : Total optimization runs triggered.
    portfolio_reviews :       Total review requests processed.
    workflow_successes :       Workflows that completed successfully.
    workflow_failures :        Workflows that failed.

    Availability
    ------------
    lifecycle_available :     Lifecycle component available.
    engine_available :         Engine component available.
    policy_available :         Policy component available.
    optimization_available :   Optimization component available.
    snapshot_available :       Snapshot component available.

    Averages
    --------
    avg_response_time_ms :    Rolling average workflow duration.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_counters()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_request(self) -> None:
        with self._lock:
            self._portfolio_requests += 1

    def record_session_created(self) -> None:
        with self._lock:
            self._portfolio_sessions += 1

    def record_snapshot_published(self) -> None:
        with self._lock:
            self._snapshots_published += 1

    def record_optimization(self) -> None:
        with self._lock:
            self._portfolio_optimizations += 1

    def record_review(self) -> None:
        with self._lock:
            self._portfolio_reviews += 1

    def record_success(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._workflow_successes += 1
            self._total_response_time_ms += duration_ms
            self._response_samples += 1

    def record_failure(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._workflow_failures += 1
            self._total_response_time_ms += duration_ms
            self._response_samples += 1

    def set_component_availability(
        self,
        lifecycle:    bool = False,
        engine:       bool = False,
        policy:       bool = False,
        optimization: bool = False,
        snapshot:     bool = False,
    ) -> None:
        with self._lock:
            self._lifecycle_available    = lifecycle
            self._engine_available       = engine
            self._policy_available       = policy
            self._optimization_available = optimization
            self._snapshot_available     = snapshot

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return an atomic copy of all statistics."""
        with self._lock:
            avg = (
                self._total_response_time_ms / self._response_samples
                if self._response_samples else 0.0
            )
            return {
                "portfolio_requests":      self._portfolio_requests,
                "portfolio_sessions":      self._portfolio_sessions,
                "snapshots_published":     self._snapshots_published,
                "portfolio_optimizations": self._portfolio_optimizations,
                "portfolio_reviews":       self._portfolio_reviews,
                "workflow_successes":      self._workflow_successes,
                "workflow_failures":       self._workflow_failures,
                "avg_response_time_ms":    avg,
                "subsystem_availability": {
                    "lifecycle":    self._lifecycle_available,
                    "engine":       self._engine_available,
                    "policy":       self._policy_available,
                    "optimization": self._optimization_available,
                    "snapshot":     self._snapshot_available,
                },
            }

    def reset(self) -> None:
        with self._lock:
            self._reset_counters()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _reset_counters(self) -> None:
        self._portfolio_requests      = 0
        self._portfolio_sessions      = 0
        self._snapshots_published     = 0
        self._portfolio_optimizations = 0
        self._portfolio_reviews       = 0
        self._workflow_successes      = 0
        self._workflow_failures       = 0
        self._total_response_time_ms  = 0.0
        self._response_samples        = 0
        self._lifecycle_available     = False
        self._engine_available        = False
        self._policy_available        = False
        self._optimization_available  = False
        self._snapshot_available      = False
