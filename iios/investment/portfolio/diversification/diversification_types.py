"""iios/investment/portfolio/diversification/diversification_types.py

Enumerations, constants, and the PositionData abstraction for the
Institutional Portfolio Diversification Engine.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DiversificationGrade(str, Enum):
    A = "A"   # Excellent
    B = "B"   # Good
    C = "C"   # Acceptable
    D = "D"   # Poor
    F = "F"   # Failing


class ConcentrationLevel(str, Enum):
    MINIMAL   = "minimal"    # Well-diversified
    LOW       = "low"        # Slightly concentrated
    MODERATE  = "moderate"   # Noticeably concentrated
    HIGH      = "high"       # Concentrated
    EXTREME   = "extreme"    # Dangerously concentrated


class DiversificationStatus(str, Enum):
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    FAILING   = "failing"
    UNKNOWN   = "unknown"


class AlertSeverity(str, Enum):
    INFO     = "info"
    WARNING  = "warning"
    CRITICAL = "critical"


class TrendDirection(str, Enum):
    IMPROVING   = "improving"
    STABLE      = "stable"
    DETERIORATING = "deteriorating"
    INSUFFICIENT_DATA = "insufficient_data"


class CorrelationLevel(str, Enum):
    LOW      = "low"       # < 0.3
    MODERATE = "moderate"  # 0.3 – 0.6
    HIGH     = "high"      # 0.6 – 0.8
    EXTREME  = "extreme"   # > 0.8


class ExposureCategory(str, Enum):
    SECTOR      = "sector"
    INDUSTRY    = "industry"
    ASSET_CLASS = "asset_class"
    COUNTRY     = "country"
    CURRENCY    = "currency"
    FACTOR      = "factor"
    STYLE       = "style"
    MARKET_CAP  = "market_cap"


class RunStatus(str, Enum):
    SUCCESS = "success"
    FAILED  = "failed"
    PARTIAL = "partial"


# ---------------------------------------------------------------------------
# Correlation proxy constants
# ---------------------------------------------------------------------------

CORR_SAME_SYMBOL:      float = 1.00
CORR_SAME_INDUSTRY:    float = 0.80
CORR_SAME_SECTOR:      float = 0.55
CORR_SAME_ASSET_CLASS: float = 0.30
CORR_DIFFERENT:        float = 0.10

# ---------------------------------------------------------------------------
# Diversification quality thresholds
# ---------------------------------------------------------------------------

# HHI thresholds (lower is more diversified)
HHI_MINIMAL_THRESHOLD:    float = 0.10   # ≤ 0.10 = minimal concentration
HHI_LOW_THRESHOLD:        float = 0.18   # ≤ 0.18 = low concentration
HHI_MODERATE_THRESHOLD:   float = 0.25   # ≤ 0.25 = moderate concentration
HHI_HIGH_THRESHOLD:       float = 0.40   # ≤ 0.40 = high concentration
# > 0.40 = extreme

# Top-N concentration thresholds
TOP1_WARNING_THRESHOLD:    float = 0.25   # Single position ≥ 25%
TOP5_WARNING_THRESHOLD:    float = 0.60   # Top-5 ≥ 60%
TOP10_WARNING_THRESHOLD:   float = 0.80   # Top-10 ≥ 80%

# Sector exposure limits
SECTOR_WARNING_THRESHOLD:  float = 0.35   # Single sector ≥ 35%
SECTOR_CRITICAL_THRESHOLD: float = 0.50   # Single sector ≥ 50%

# Correlation thresholds
AVG_CORR_WARNING:          float = 0.55   # Avg pairwise correlation ≥ 0.55
AVG_CORR_CRITICAL:         float = 0.70   # Avg pairwise correlation ≥ 0.70

# Quality gate
DEFAULT_QUALITY_GATE:      float = 0.55

# Schema
DIVERSIFICATION_PROFILE_SCHEMA_VERSION:  str = "1.0.0"
DIVERSIFICATION_SNAPSHOT_SCHEMA_VERSION: str = "1.0.0"


# ---------------------------------------------------------------------------
# PositionData — normalised representation consumed by all analysers
# ---------------------------------------------------------------------------

@dataclass
class PositionData:
    """
    Normalized position record consumed by diversification analysers.
    Extracted from either OptimizationPlan.positions or AllocationPlan.allocations.
    """

    symbol:      str   = ""
    weight:      float = 0.0    # portfolio weight in [0, 1]
    sector:      str   = "unknown"
    industry:    str   = "unknown"
    asset_class: str   = "equity"
    country:     str   = "india"
    currency:    str   = "INR"
    risk_score:  float = 0.5    # 0 = no risk, 1 = maximum risk
    conviction:  float = 0.5    # 0 = no conviction, 1 = full conviction
    confidence:  float = 0.5    # 0 = no confidence, 1 = full confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":      self.symbol,
            "weight":      round(self.weight, 6),
            "sector":      self.sector,
            "industry":    self.industry,
            "asset_class": self.asset_class,
            "country":     self.country,
            "currency":    self.currency,
            "risk_score":  round(self.risk_score, 4),
            "conviction":  round(self.conviction, 4),
            "confidence":  round(self.confidence, 4),
        }


# ---------------------------------------------------------------------------
# Factory helpers — extract PositionData from upstream plan objects
# ---------------------------------------------------------------------------

def positions_from_plan(plan: Any) -> List[PositionData]:
    """
    Duck-typed extractor: accepts OptimizationPlan, AllocationPlan,
    or any object with an iterable `positions` or `allocations` attribute.
    """
    raw = getattr(plan, "positions", None) or getattr(plan, "allocations", [])
    result: List[PositionData] = []
    for p in raw:
        w = float(
            getattr(p, "optimized_weight",
            getattr(p, "allocated_weight",
            getattr(p, "weight", 0.0)))
        )
        ac_raw = getattr(p, "asset_class", "equity")
        ac = str(getattr(ac_raw, "value", ac_raw))
        result.append(PositionData(
            symbol      = str(getattr(p, "symbol", "")),
            weight      = max(0.0, w),
            sector      = str(getattr(p, "sector", "unknown")),
            industry    = str(getattr(p, "industry", "unknown")),
            asset_class = ac,
            country     = str(getattr(p, "country", "india")),
            currency    = str(getattr(p, "currency", "INR")),
            risk_score  = float(getattr(p, "risk_proxy",
                                 getattr(p, "risk_score", 0.5))),
            conviction  = float(getattr(p, "expected_return_proxy",
                                 getattr(p, "conviction", 0.5))),
            confidence  = float(getattr(p, "confidence_proxy",
                                 getattr(p, "confidence", 0.5))),
        ))
    # Renormalize weights if they don't sum to 1
    total = sum(p.weight for p in result)
    if total > 1e-8 and abs(total - 1.0) > 1e-4:
        for pos in result:
            pos.weight = pos.weight / total
    return result


# ---------------------------------------------------------------------------
# Utility: concentration level from HHI
# ---------------------------------------------------------------------------

def hhi_to_concentration_level(hhi: float) -> ConcentrationLevel:
    if hhi <= HHI_MINIMAL_THRESHOLD:
        return ConcentrationLevel.MINIMAL
    if hhi <= HHI_LOW_THRESHOLD:
        return ConcentrationLevel.LOW
    if hhi <= HHI_MODERATE_THRESHOLD:
        return ConcentrationLevel.MODERATE
    if hhi <= HHI_HIGH_THRESHOLD:
        return ConcentrationLevel.HIGH
    return ConcentrationLevel.EXTREME


def compute_entropy(weights: List[float]) -> float:
    """Shannon entropy of a weight distribution."""
    return -sum(w * math.log(max(w, 1e-10)) for w in weights if w > 1e-10)


def compute_hhi(weights: List[float]) -> float:
    """Herfindahl-Hirschman Index."""
    return sum(w * w for w in weights)


def effective_n(weights: List[float]) -> float:
    """Effective number of uncorrelated positions = 1 / HHI."""
    hhi = compute_hhi(weights)
    return 1.0 / max(hhi, 1e-10)
