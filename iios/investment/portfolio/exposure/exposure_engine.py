"""iios/investment/portfolio/exposure/exposure_engine.py
Orchestrates exposure tracking across a portfolio.
"""
from __future__ import annotations

import threading

from iios.investment.portfolio.core.portfolio import Portfolio
from iios.investment.portfolio.exposure.exposure_limits import ExposureLimits
from iios.investment.portfolio.exposure.exposure_report import ExposureReport
from iios.investment.portfolio.exposure.exposure_tracker import ExposureTracker


class ExposureEngine:
    """
    Top-level exposure intelligence coordinator.
    Wraps ExposureTracker and manages per-portfolio limit configs.
    """

    def __init__(
        self,
        tracker: ExposureTracker | None = None,
        default_limits: ExposureLimits | None = None,
    ) -> None:
        self._lock:           threading.RLock               = threading.RLock()
        self._tracker:        ExposureTracker               = tracker or ExposureTracker()
        self._default_limits: ExposureLimits                = default_limits or ExposureLimits()
        self._portfolio_limits: dict[str, ExposureLimits]   = {}

    def set_limits(self, portfolio_id: str, limits: ExposureLimits) -> None:
        with self._lock:
            self._portfolio_limits[portfolio_id] = limits

    def get_limits(self, portfolio_id: str) -> ExposureLimits:
        with self._lock:
            return self._portfolio_limits.get(portfolio_id, self._default_limits)

    def analyze(
        self,
        portfolio: Portfolio,
        limits:    ExposureLimits | None = None,
    ) -> ExposureReport:
        effective_limits = limits or self.get_limits(portfolio.portfolio_id)
        return self._tracker.compute(portfolio, effective_limits)
