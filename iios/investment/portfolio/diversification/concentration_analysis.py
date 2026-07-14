"""iios/investment/portfolio/diversification/concentration_analysis.py

Position-level, sector-level, industry-level, and asset-class-level
concentration analysis.  All pure-Python, no external dependencies.
"""
from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.diversification.diversification_types import (
    ConcentrationLevel,
    compute_entropy,
    compute_hhi,
    effective_n,
    hhi_to_concentration_level,
    PositionData,
)


# ---------------------------------------------------------------------------
# Position concentration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PositionConcentrationResult:
    """Concentration metrics at the individual position level."""

    n_positions:    int   = 0
    effective_n:    float = 0.0
    hhi:            float = 0.0
    entropy:        float = 0.0
    top1_weight:    float = 0.0   # largest single position
    top5_weight:    float = 0.0   # top-5 combined
    top10_weight:   float = 0.0   # top-10 combined
    top1_symbol:    str   = ""
    concentration_level: ConcentrationLevel = ConcentrationLevel.MODERATE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_positions":         self.n_positions,
            "effective_n":         round(self.effective_n, 2),
            "hhi":                 round(self.hhi, 6),
            "entropy":             round(self.entropy, 4),
            "top1_weight":         round(self.top1_weight, 4),
            "top5_weight":         round(self.top5_weight, 4),
            "top10_weight":        round(self.top10_weight, 4),
            "top1_symbol":         self.top1_symbol,
            "concentration_level": self.concentration_level.value,
        }


def analyze_position_concentration(
    positions: List[PositionData],
) -> PositionConcentrationResult:
    """Compute position-level concentration metrics."""
    if not positions:
        return PositionConcentrationResult()

    sorted_pos = sorted(positions, key=lambda p: p.weight, reverse=True)
    weights    = [p.weight for p in positions]
    sorted_w   = [p.weight for p in sorted_pos]

    hhi_val  = compute_hhi(weights)
    ent_val  = compute_entropy(weights)
    eff_n    = 1.0 / max(hhi_val, 1e-10)

    top1_w   = sorted_w[0] if len(sorted_w) >= 1 else 0.0
    top5_w   = sum(sorted_w[:5])
    top10_w  = sum(sorted_w[:10])

    return PositionConcentrationResult(
        n_positions         = len(positions),
        effective_n         = round(eff_n, 4),
        hhi                 = round(hhi_val, 6),
        entropy             = round(ent_val, 4),
        top1_weight         = round(top1_w, 4),
        top5_weight         = round(top5_w, 4),
        top10_weight        = round(top10_w, 4),
        top1_symbol         = sorted_pos[0].symbol if sorted_pos else "",
        concentration_level = hhi_to_concentration_level(hhi_val),
    )


# ---------------------------------------------------------------------------
# Sector / industry / asset-class / country / currency concentration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExposureConcentrationResult:
    """Concentration metrics for a given exposure dimension (sector, industry, etc.)."""

    dimension:          str                    = ""
    bucket_weights:     Dict[str, float]       = field(default_factory=dict)
    n_buckets:          int                    = 0
    hhi:                float                  = 0.0
    entropy:            float                  = 0.0
    effective_n:        float                  = 0.0
    top1_weight:        float                  = 0.0
    top1_bucket:        str                    = ""
    concentration_level:ConcentrationLevel     = ConcentrationLevel.MODERATE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension":           self.dimension,
            "bucket_weights":      {k: round(v, 4) for k, v in self.bucket_weights.items()},
            "n_buckets":           self.n_buckets,
            "hhi":                 round(self.hhi, 6),
            "entropy":             round(self.entropy, 4),
            "effective_n":         round(self.effective_n, 2),
            "top1_weight":         round(self.top1_weight, 4),
            "top1_bucket":         self.top1_bucket,
            "concentration_level": self.concentration_level.value,
        }


def _aggregate_by(positions: List[PositionData], key: str) -> Dict[str, float]:
    buckets: Dict[str, float] = {}
    for p in positions:
        k = getattr(p, key, "unknown")
        buckets[k] = buckets.get(k, 0.0) + p.weight
    return buckets


def analyze_exposure_concentration(
    positions: List[PositionData],
    dimension: str,                  # "sector" | "industry" | "asset_class" | "country" | "currency"
) -> ExposureConcentrationResult:
    """Concentration across a single exposure dimension."""
    if not positions:
        return ExposureConcentrationResult(dimension=dimension)

    buckets = _aggregate_by(positions, dimension)
    weights = list(buckets.values())

    hhi_val = compute_hhi(weights)
    ent_val = compute_entropy(weights)
    eff_n   = 1.0 / max(hhi_val, 1e-10)
    top1_b  = max(buckets, key=buckets.get) if buckets else ""
    top1_w  = buckets.get(top1_b, 0.0)

    return ExposureConcentrationResult(
        dimension           = dimension,
        bucket_weights      = {k: round(v, 4) for k, v in buckets.items()},
        n_buckets           = len(buckets),
        hhi                 = round(hhi_val, 6),
        entropy             = round(ent_val, 4),
        effective_n         = round(eff_n, 2),
        top1_weight         = round(top1_w, 4),
        top1_bucket         = top1_b,
        concentration_level = hhi_to_concentration_level(hhi_val),
    )
