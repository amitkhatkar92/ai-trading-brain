"""features/feature_statistics.py — Statistical summary of a feature set."""
from __future__ import annotations

import statistics as _stats
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class FeatureStatistics:
    """
    Statistical summary for one numeric feature across a dataset.

    Used by the FeatureStore and FeatureEngine to detect distribution shifts.
    """
    name:         str
    count:        int
    mean:         Optional[float]
    std:          Optional[float]
    min_val:      Optional[float]
    max_val:      Optional[float]
    p25:          Optional[float]
    p50:          Optional[float]
    p75:          Optional[float]
    missing_rate: float

    @classmethod
    def compute(cls, name: str, values: list[float]) -> "FeatureStatistics":
        n = len(values)
        if n == 0:
            return cls(name=name, count=0, mean=None, std=None,
                       min_val=None, max_val=None, p25=None, p50=None, p75=None,
                       missing_rate=1.0)
        sorted_v  = sorted(values)
        mean_v    = sum(values) / n
        std_v     = _stats.stdev(values) if n >= 2 else 0.0
        p25_v     = sorted_v[int(n * 0.25)]
        p50_v     = sorted_v[int(n * 0.50)]
        p75_v     = sorted_v[int(n * 0.75)]
        return cls(
            name         = name,
            count        = n,
            mean         = mean_v,
            std          = std_v,
            min_val      = sorted_v[0],
            max_val      = sorted_v[-1],
            p25          = p25_v,
            p50          = p50_v,
            p75          = p75_v,
            missing_rate = 0.0,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":         self.name,
            "count":        self.count,
            "mean":         self.mean,
            "std":          self.std,
            "min":          self.min_val,
            "max":          self.max_val,
            "p25":          self.p25,
            "p50":          self.p50,
            "p75":          self.p75,
            "missing_rate": self.missing_rate,
        }
