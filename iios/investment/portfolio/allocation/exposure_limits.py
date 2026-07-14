"""iios/investment/portfolio/allocation/exposure_limits.py

Portfolio-level exposure limit checks for sectors, industries, asset classes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ExposureOutcome(str, Enum):
    PASSED  = "passed"
    WARNING = "warning"
    VIOLATED= "violated"


@dataclass(frozen=True)
class ExposureCheck:
    """Result of a single exposure limit check."""

    dimension:  str              = ""     # "sector" | "asset_class" | "industry"
    key:        str              = ""     # The sector/industry/asset-class name
    outcome:    ExposureOutcome  = ExposureOutcome.PASSED
    actual_pct: float            = 0.0   # Actual weight as fraction
    limit_pct:  float            = 0.0   # Limit as fraction
    excess_pct: float            = 0.0   # max(0, actual_pct - limit_pct)
    message:    str              = ""

    @property
    def passed(self) -> bool:
        return self.outcome == ExposureOutcome.PASSED

    @property
    def is_violation(self) -> bool:
        return self.outcome == ExposureOutcome.VIOLATED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension":  self.dimension,
            "key":        self.key,
            "outcome":    self.outcome.value,
            "actual_pct": round(self.actual_pct, 6),
            "limit_pct":  round(self.limit_pct, 6),
            "excess_pct": round(self.excess_pct, 6),
            "message":    self.message,
        }


class ExposureLimitChecker:
    """
    Checks sector, asset-class, and industry exposure against policy limits.
    All inputs are weight fractions (not dollars).
    """

    # A check is a WARNING when excess ≤ this (fraction), VIOLATED otherwise
    _WARNING_TOLERANCE: float = 0.01   # 1 %

    def check_sector(
        self,
        sector_weights: Dict[str, float],   # sector → fraction of total
        max_sector_pct:  float,
    ) -> List[ExposureCheck]:
        return self._check_dimension("sector", sector_weights, max_sector_pct)

    def check_industry(
        self,
        industry_weights: Dict[str, float],
        max_industry_pct: float,
    ) -> List[ExposureCheck]:
        return self._check_dimension("industry", industry_weights, max_industry_pct)

    def check_asset_class(
        self,
        asset_class_weights: Dict[str, float],
        max_asset_class_pct: float,
    ) -> List[ExposureCheck]:
        return self._check_dimension("asset_class", asset_class_weights, max_asset_class_pct)

    def check_all(
        self,
        sector_weights:      Dict[str, float],
        asset_class_weights: Dict[str, float],
        max_sector_pct:      float,
        max_asset_class_pct: float,
        industry_weights:    Optional[Dict[str, float]] = None,
        max_industry_pct:    float = 0.25,
    ) -> List[ExposureCheck]:
        checks: List[ExposureCheck] = []
        checks.extend(self.check_sector(sector_weights, max_sector_pct))
        checks.extend(self.check_asset_class(asset_class_weights, max_asset_class_pct))
        if industry_weights:
            checks.extend(self.check_industry(industry_weights, max_industry_pct))
        return checks

    # ------------------------------------------------------------------
    def _check_dimension(
        self,
        dimension: str,
        weights:   Dict[str, float],
        limit:     float,
    ) -> List[ExposureCheck]:
        checks: List[ExposureCheck] = []
        for key, weight in weights.items():
            if weight <= 0:
                continue
            excess = max(0.0, weight - limit)
            if excess == 0.0:
                outcome = ExposureOutcome.PASSED
                msg     = f"{dimension}:{key} {weight:.1%} within {limit:.1%} limit"
            elif excess <= self._WARNING_TOLERANCE:
                outcome = ExposureOutcome.WARNING
                msg     = f"{dimension}:{key} {weight:.1%} slightly over {limit:.1%} limit by {excess:.1%}"
            else:
                outcome = ExposureOutcome.VIOLATED
                msg     = f"{dimension}:{key} {weight:.1%} exceeds {limit:.1%} limit by {excess:.1%}"
            checks.append(ExposureCheck(
                dimension  = dimension,
                key        = key,
                outcome    = outcome,
                actual_pct = weight,
                limit_pct  = limit,
                excess_pct = excess,
                message    = msg,
            ))
        return checks
