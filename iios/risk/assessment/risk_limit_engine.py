"""
risk_limit_engine.py — iios.risk.assessment
=============================================
Risk limit utilisation engine.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    LIMIT_BREACH_THRESHOLD,
    LIMIT_CRITICAL_THRESHOLD,
    LIMIT_WARNING_THRESHOLD,
    LimitStatus,
    VERSION,
)
from .exceptions import RiskCalculationError


class LimitUtilisationResult:
    """Result of a single limit utilisation check."""
    __slots__ = ("limit_name", "current_value", "limit_value",
                 "utilisation", "status", "breach_amount")

    def __init__(
        self,
        limit_name:    str,
        current_value: float,
        limit_value:   float,
    ) -> None:
        self.limit_name    = limit_name
        self.current_value = current_value
        self.limit_value   = limit_value
        self.utilisation   = (
            current_value / limit_value if limit_value > 0 else 0.0
        )
        self.breach_amount = max(0.0, current_value - limit_value)
        self.status        = self._classify(self.utilisation)

    @staticmethod
    def _classify(util: float) -> LimitStatus:
        if util >= LIMIT_CRITICAL_THRESHOLD:
            return LimitStatus.CRITICAL
        if util >= LIMIT_BREACH_THRESHOLD:
            return LimitStatus.BREACH
        if util >= LIMIT_WARNING_THRESHOLD:
            return LimitStatus.WARNING
        return LimitStatus.OK

    def to_dict(self) -> Dict[str, Any]:
        return {
            "limit_name":    self.limit_name,
            "current_value": self.current_value,
            "limit_value":   self.limit_value,
            "utilisation":   self.utilisation,
            "status":        self.status.value,
            "breach_amount": self.breach_amount,
        }


class RiskLimitEngine:
    """
    Risk limit utilisation engine.

    Compares current risk metrics against defined limits and reports
    utilisation levels.  Purely analytical — no execution or policy checks.
    """

    VERSION: str = VERSION

    # ------------------------------------------------------------------
    # Single limit check
    # ------------------------------------------------------------------

    def check_limit(
        self,
        limit_name:    str,
        current_value: float,
        limit_value:   float,
    ) -> LimitUtilisationResult:
        """Check a single named limit."""
        if limit_value < 0:
            raise RiskCalculationError(
                f"Limit value must be non-negative for '{limit_name}', got {limit_value}",
                engine="LimitEngine",
            )
        return LimitUtilisationResult(limit_name, current_value, limit_value)

    # ------------------------------------------------------------------
    # Batch limit check
    # ------------------------------------------------------------------

    def check_all_limits(
        self,
        current_values: Dict[str, float],
        limits:         Dict[str, float],
    ) -> Dict[str, LimitUtilisationResult]:
        """
        Check all limits that appear in both ``current_values`` and ``limits``.

        Returns dict of limit_name → :class:`LimitUtilisationResult`.
        """
        results = {}
        for name in limits:
            if name in current_values:
                results[name] = self.check_limit(name, current_values[name], limits[name])
        return results

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summarise(
        self,
        results: Dict[str, LimitUtilisationResult],
    ) -> Dict[str, Any]:
        """High-level summary of all limit checks."""
        breaches  = [n for n, r in results.items() if r.status in (LimitStatus.BREACH, LimitStatus.CRITICAL)]
        warnings  = [n for n, r in results.items() if r.status == LimitStatus.WARNING]
        max_util  = max((r.utilisation for r in results.values()), default=0.0)
        return {
            "total_limits":     len(results),
            "breaches":         breaches,
            "breach_count":     len(breaches),
            "warnings":         warnings,
            "warning_count":    len(warnings),
            "max_utilisation":  max_util,
            "all_ok":           all(r.status == LimitStatus.OK for r in results.values()),
        }

    # ------------------------------------------------------------------
    # Derive VaR limit utilisation
    # ------------------------------------------------------------------

    def calculate_var_limit_utilisation(
        self,
        var_value:   float,
        var_limit:   float,
    ) -> LimitUtilisationResult:
        """Convenience: check VaR against a VaR limit."""
        return self.check_limit("var_limit", var_value, var_limit)
