"""iios/investment/portfolio/rebalancing/exposure_drift.py

Exposure drift: sector, country, currency, asset-class, strategy drift.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.rebalancing.rebalancing_types import (
    CurrentPosition, DriftLevel, TargetPosition,
    classify_drift_level, now_utc,
)


@dataclass(frozen=True)
class ExposureBucketDrift:
    """Drift in a single exposure bucket (e.g. a sector)."""

    bucket_name:      str
    current_weight:   float = 0.0
    target_weight:    float = 0.0
    drift:            float = 0.0    # signed: current - target
    abs_drift:        float = 0.0
    drift_level:      DriftLevel = DriftLevel.NONE
    is_overweight:    bool = False
    is_underweight:   bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bucket":        self.bucket_name,
            "current_weight":round(self.current_weight, 4),
            "target_weight": round(self.target_weight, 4),
            "drift":         round(self.drift, 4),
            "drift_level":   self.drift_level.value,
        }


@dataclass(frozen=True)
class ExposureDrift:
    """Complete exposure drift across all dimensions."""

    result_id:         str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:      str   = ""
    created_at:        str   = field(default_factory=now_utc)

    # By dimension
    sector_drifts:     tuple = field(default_factory=tuple)   # ExposureBucketDrift
    country_drifts:    tuple = field(default_factory=tuple)
    currency_drifts:   tuple = field(default_factory=tuple)
    asset_class_drifts:tuple = field(default_factory=tuple)
    strategy_drifts:   tuple = field(default_factory=tuple)

    # Aggregate
    max_sector_drift:      float      = 0.0
    max_country_drift:     float      = 0.0
    max_currency_drift:    float      = 0.0
    overall_drift_level:   DriftLevel = DriftLevel.NONE
    most_drifted_sector:   str        = ""
    most_drifted_country:  str        = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_sector_drift":   round(self.max_sector_drift, 4),
            "max_country_drift":  round(self.max_country_drift, 4),
            "overall_drift_level":self.overall_drift_level.value,
            "most_drifted_sector":self.most_drifted_sector,
            "sector_drifts":      [d.to_dict() for d in self.sector_drifts],
            "country_drifts":     [d.to_dict() for d in self.country_drifts],
        }


def compute_exposure_drift(
    current:      List[CurrentPosition],
    target:       List[TargetPosition],
    portfolio_id: str = "",
) -> ExposureDrift:
    """
    Compute exposure drift across sector, country, currency, asset class, strategy.
    """
    sec_drifts = _compute_dimension_drifts(
        {p.symbol: (p.current_weight, p.sector) for p in current},
        {p.symbol: (p.target_weight, p.sector)  for p in target},
    )
    cty_drifts = _compute_dimension_drifts(
        {p.symbol: (p.current_weight, p.country) for p in current},
        {p.symbol: (p.target_weight, p.country)  for p in target},
    )
    cur_drifts = _compute_dimension_drifts(
        {p.symbol: (p.current_weight, p.currency) for p in current},
        {p.symbol: (p.target_weight, p.currency)  for p in target},
    )
    ac_drifts = _compute_dimension_drifts(
        {p.symbol: (p.current_weight, p.asset_class) for p in current},
        {p.symbol: (p.target_weight, p.asset_class)  for p in target},
    )
    strat_drifts = _compute_dimension_drifts(
        {p.symbol: (p.current_weight, p.strategy_id) for p in current},
        {p.symbol: (p.target_weight, p.strategy_id)  for p in target},
    )

    max_sec = max((d.abs_drift for d in sec_drifts), default=0.0)
    max_cty = max((d.abs_drift for d in cty_drifts), default=0.0)
    max_cur = max((d.abs_drift for d in cur_drifts), default=0.0)
    overall = classify_drift_level(max(max_sec, max_cty))

    top_sec = sec_drifts[0].bucket_name if sec_drifts else ""
    top_cty = cty_drifts[0].bucket_name if cty_drifts else ""

    return ExposureDrift(
        portfolio_id        = portfolio_id,
        sector_drifts       = tuple(sec_drifts),
        country_drifts      = tuple(cty_drifts),
        currency_drifts     = tuple(cur_drifts),
        asset_class_drifts  = tuple(ac_drifts),
        strategy_drifts     = tuple(strat_drifts),
        max_sector_drift    = round(max_sec, 6),
        max_country_drift   = round(max_cty, 6),
        max_currency_drift  = round(max_cur, 6),
        overall_drift_level = overall,
        most_drifted_sector = top_sec,
        most_drifted_country= top_cty,
    )


def _compute_dimension_drifts(
    current_map: Dict[str, tuple],   # symbol → (weight, bucket)
    target_map:  Dict[str, tuple],
) -> List[ExposureBucketDrift]:
    """Aggregate current and target weights by bucket, compute drift."""
    cur_buckets: Dict[str, float] = {}
    tgt_buckets: Dict[str, float] = {}

    for sym, (w, bucket) in current_map.items():
        bucket = bucket or "unknown"
        cur_buckets[bucket] = cur_buckets.get(bucket, 0.0) + w

    for sym, (w, bucket) in target_map.items():
        bucket = bucket or "unknown"
        tgt_buckets[bucket] = tgt_buckets.get(bucket, 0.0) + w

    all_buckets = sorted(set(cur_buckets.keys()) | set(tgt_buckets.keys()))
    result = []
    for b in all_buckets:
        cw = cur_buckets.get(b, 0.0)
        tw = tgt_buckets.get(b, 0.0)
        d  = cw - tw
        ad = abs(d)
        result.append(ExposureBucketDrift(
            bucket_name    = b,
            current_weight = round(cw, 6),
            target_weight  = round(tw, 6),
            drift          = round(d, 6),
            abs_drift      = round(ad, 6),
            drift_level    = classify_drift_level(ad),
            is_overweight  = d > 0,
            is_underweight = d < 0,
        ))
    return sorted(result, key=lambda x: x.abs_drift, reverse=True)
