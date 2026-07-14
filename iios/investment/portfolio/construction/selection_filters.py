"""iios/investment/portfolio/construction/selection_filters.py

Composable filter chain for InvestmentRecommendations.

Each filter is a pure function: (recommendation, request) → bool.
The FilterChain applies all registered filters and returns the surviving
recommendations along with a FilterResult audit trail.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.construction.construction_types import (
    AssetClass,
    ConstructionDirection,
    MarketCapCategory,
)


# ---------------------------------------------------------------------------
# FilterResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FilterOutcome:
    """Result of applying one filter to one recommendation."""

    symbol:       str   = ""
    filter_name:  str   = ""
    passed:       bool  = True
    reason:       str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":      self.symbol,
            "filter_name": self.filter_name,
            "passed":      self.passed,
            "reason":      self.reason,
        }


@dataclass(frozen=True)
class FilterResult:
    """Aggregate output of the FilterChain applied to a list of recommendations."""

    total_in:       int                      = 0
    total_out:      int                      = 0
    rejected_count: int                      = 0
    filter_names:   Tuple[str, ...]          = field(default_factory=tuple)
    rejections:     Tuple[FilterOutcome, ...]= field(default_factory=tuple)

    @property
    def pass_rate(self) -> float:
        return self.total_out / self.total_in if self.total_in > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_in":       self.total_in,
            "total_out":      self.total_out,
            "rejected_count": self.rejected_count,
            "pass_rate":      round(self.pass_rate, 4),
            "filter_names":   list(self.filter_names),
            "rejections":     [r.to_dict() for r in self.rejections],
        }


# ---------------------------------------------------------------------------
# Abstract filter
# ---------------------------------------------------------------------------

class SelectionFilter(abc.ABC):
    """Abstract base for a single recommendation filter."""

    @property
    @abc.abstractmethod
    def filter_name(self) -> str: ...

    @abc.abstractmethod
    def passes(self, rec: Any, request: Any) -> Tuple[bool, str]:
        """
        Returns (passes: bool, reason: str).
        reason is empty when the filter passes.
        """
        ...


# ---------------------------------------------------------------------------
# Concrete filters
# ---------------------------------------------------------------------------

class MinConvictionFilter(SelectionFilter):
    """Exclude recommendations with conviction < request.min_conviction."""

    @property
    def filter_name(self) -> str:
        return "min_conviction"

    def passes(self, rec: Any, request: Any) -> Tuple[bool, str]:
        if rec.conviction < request.min_conviction:
            return False, f"conviction {rec.conviction:.3f} < min {request.min_conviction:.3f}"
        return True, ""


class MinConfidenceFilter(SelectionFilter):
    """Exclude recommendations with confidence < request.min_confidence."""

    @property
    def filter_name(self) -> str:
        return "min_confidence"

    def passes(self, rec: Any, request: Any) -> Tuple[bool, str]:
        if rec.confidence < request.min_confidence:
            return False, f"confidence {rec.confidence:.3f} < min {request.min_confidence:.3f}"
        return True, ""


class MaxRiskScoreFilter(SelectionFilter):
    """Exclude recommendations with risk_score > request.max_risk_score."""

    @property
    def filter_name(self) -> str:
        return "max_risk_score"

    def passes(self, rec: Any, request: Any) -> Tuple[bool, str]:
        if rec.risk_score > request.max_risk_score:
            return False, f"risk_score {rec.risk_score:.3f} > max {request.max_risk_score:.3f}"
        return True, ""


class DirectionFilter(SelectionFilter):
    """
    Filter by allowed direction.

    For LONG_ONLY construction, SHORT recommendations are excluded.
    For LONG_SHORT, both are accepted.
    """

    @property
    def filter_name(self) -> str:
        return "direction"

    def passes(self, rec: Any, request: Any) -> Tuple[bool, str]:
        from iios.investment.portfolio.construction.construction_types import ConstructionType
        ct = request.construction_type
        if ct in (ConstructionType.LONG_ONLY, ConstructionType.ETF_LIKE,
                  ConstructionType.INCOME, ConstructionType.GROWTH,
                  ConstructionType.SECTOR, ConstructionType.MULTI_ASSET):
            if rec.direction == ConstructionDirection.SHORT:
                return False, "short positions not allowed for this construction type"
        if rec.direction == ConstructionDirection.SHORT and not request.allow_short:
            return False, "allow_short=False in request"
        return True, ""


class SectorAllowlistFilter(SelectionFilter):
    """Only pass recommendations in allowed sectors (empty = allow all)."""

    @property
    def filter_name(self) -> str:
        return "sector_allowlist"

    def passes(self, rec: Any, request: Any) -> Tuple[bool, str]:
        allowed   = request.sectors_allowed
        excluded  = request.sectors_excluded
        if rec.sector in excluded:
            return False, f"sector '{rec.sector}' is excluded"
        if allowed and rec.sector not in allowed:
            return False, f"sector '{rec.sector}' not in allowed set"
        return True, ""


class AssetClassFilter(SelectionFilter):
    """Only pass recommendations with an allowed asset class (empty = allow all)."""

    @property
    def filter_name(self) -> str:
        return "asset_class"

    def passes(self, rec: Any, request: Any) -> Tuple[bool, str]:
        allowed = request.asset_classes_allowed
        if allowed and rec.asset_class not in allowed:
            return False, f"asset_class {rec.asset_class.value} not in allowed set"
        return True, ""


class MarketCapFilter(SelectionFilter):
    """Only pass recommendations with an allowed market cap (empty = allow all)."""

    @property
    def filter_name(self) -> str:
        return "market_cap"

    def passes(self, rec: Any, request: Any) -> Tuple[bool, str]:
        allowed = request.market_caps_allowed
        if allowed and rec.market_cap_category not in allowed:
            return False, f"market_cap {rec.market_cap_category.value} not in allowed set"
        return True, ""


class ExpiryFilter(SelectionFilter):
    """Exclude expired recommendations."""

    @property
    def filter_name(self) -> str:
        return "expiry"

    def passes(self, rec: Any, request: Any) -> Tuple[bool, str]:
        if rec.is_expired:
            return False, "recommendation is expired"
        return True, ""


class DuplicateSymbolFilter(SelectionFilter):
    """
    Stateful: keeps the highest-scoring recommendation per symbol.
    Must be the LAST filter in the chain.
    """

    def __init__(self) -> None:
        self._seen: Dict[str, Tuple[Any, float]] = {}  # symbol → (rec, score)

    @property
    def filter_name(self) -> str:
        return "duplicate_symbol"

    def reset(self) -> None:
        self._seen.clear()

    def passes(self, rec: Any, request: Any) -> Tuple[bool, str]:
        sym   = rec.symbol
        score = rec.composite_score
        if sym not in self._seen:
            self._seen[sym] = (rec, score)
            return True, ""
        _, best_score = self._seen[sym]
        if score > best_score:
            self._seen[sym] = (rec, score)
            return True, ""
        return False, f"duplicate: {sym} has better recommendation already selected"


# ---------------------------------------------------------------------------
# FilterChain
# ---------------------------------------------------------------------------

class FilterChain:
    """
    Applies an ordered list of SelectionFilters to a list of recommendations.

    Usage::

        chain  = FilterChain.default()
        passed, result = chain.apply(recommendations, request)
    """

    def __init__(self, filters: Optional[List[SelectionFilter]] = None) -> None:
        self._filters: List[SelectionFilter] = list(filters or [])

    def add(self, f: SelectionFilter) -> "FilterChain":
        self._filters.append(f)
        return self

    @property
    def filter_names(self) -> List[str]:
        return [f.filter_name for f in self._filters]

    def apply(
        self,
        recommendations: List[Any],
        request: Any,
    ) -> Tuple[List[Any], FilterResult]:
        """
        Apply all filters; return (surviving_recs, FilterResult).
        Deterministic: input order is preserved.
        """
        # Reset any stateful filters
        for f in self._filters:
            if hasattr(f, "reset"):
                f.reset()

        passed:     List[Any]          = []
        rejections: List[FilterOutcome]= []

        for rec in recommendations:
            rejected = False
            for filt in self._filters:
                ok, reason = filt.passes(rec, request)
                if not ok:
                    rejections.append(FilterOutcome(
                        symbol=rec.symbol,
                        filter_name=filt.filter_name,
                        passed=False,
                        reason=reason,
                    ))
                    rejected = True
                    break
            if not rejected:
                passed.append(rec)

        result = FilterResult(
            total_in=len(recommendations),
            total_out=len(passed),
            rejected_count=len(rejections),
            filter_names=tuple(self.filter_names),
            rejections=tuple(rejections),
        )
        return passed, result

    @classmethod
    def default(cls) -> "FilterChain":
        """Standard filter chain for long-only portfolios."""
        return cls([
            ExpiryFilter(),
            MinConvictionFilter(),
            MinConfidenceFilter(),
            MaxRiskScoreFilter(),
            DirectionFilter(),
            SectorAllowlistFilter(),
            AssetClassFilter(),
            MarketCapFilter(),
            DuplicateSymbolFilter(),
        ])
