"""datasets/dataset_statistics.py — Statistical summary of a dataset."""
from __future__ import annotations

import statistics as _stats
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class DatasetStatistics:
    """
    Statistical summary of a dataset.

    Numeric features provide means, stds, and min/max.
    Categorical features provide value counts.
    """
    total_records:      int
    feature_count:      int
    label_distribution: dict[str, int]     # {label → count}
    feature_means:      dict[str, float]
    feature_stds:       dict[str, float]
    feature_mins:       dict[str, float]
    feature_maxs:       dict[str, float]
    missing_rates:      dict[str, float]   # {feature → fraction missing}
    class_balance:      Optional[float]    # None for regression; fraction of majority class
    has_timestamps:     bool
    time_range:         Optional[tuple[float, float]]  # (min_ts, max_ts)

    @classmethod
    def compute(
        cls,
        records:       list[dict[str, Any]],
        feature_names: list[str],
        label_name:    Optional[str],
        *,
        has_timestamps: bool = False,
    ) -> "DatasetStatistics":
        """Compute statistics from a list of record dicts."""
        n = len(records)
        if n == 0:
            return cls(
                total_records   = 0,
                feature_count   = len(feature_names),
                label_distribution = {},
                feature_means   = {},
                feature_stds    = {},
                feature_mins    = {},
                feature_maxs    = {},
                missing_rates   = {},
                class_balance   = None,
                has_timestamps  = has_timestamps,
                time_range      = None,
            )

        means: dict[str, float] = {}
        stds:  dict[str, float] = {}
        mins:  dict[str, float] = {}
        maxs:  dict[str, float] = {}
        missing: dict[str, float] = {}

        for feat in feature_names:
            values = [r[feat] for r in records if feat in r and isinstance(r[feat], (int, float))]
            miss   = 1.0 - len(values) / n
            missing[feat] = miss
            if values:
                means[feat] = sum(values) / len(values)
                stds[feat]  = _stats.stdev(values) if len(values) >= 2 else 0.0
                mins[feat]  = min(values)
                maxs[feat]  = max(values)

        label_dist: dict[str, int] = {}
        if label_name:
            for r in records:
                lv = r.get(label_name)
                if lv is not None:
                    key = str(lv)
                    label_dist[key] = label_dist.get(key, 0) + 1

        # Class balance: fraction of majority class
        balance = None
        if label_dist:
            total_labeled = sum(label_dist.values())
            if total_labeled > 0:
                balance = max(label_dist.values()) / total_labeled

        ts_range = None
        if has_timestamps:
            tss = [r.get("timestamp") for r in records if isinstance(r.get("timestamp"), float)]
            if tss:
                ts_range = (min(tss), max(tss))

        return cls(
            total_records      = n,
            feature_count      = len(feature_names),
            label_distribution = label_dist,
            feature_means      = means,
            feature_stds       = stds,
            feature_mins       = mins,
            feature_maxs       = maxs,
            missing_rates      = missing,
            class_balance      = balance,
            has_timestamps     = has_timestamps,
            time_range         = ts_range,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_records":      self.total_records,
            "feature_count":      self.feature_count,
            "label_distribution": self.label_distribution,
            "feature_means":      self.feature_means,
            "feature_stds":       self.feature_stds,
            "feature_mins":       self.feature_mins,
            "feature_maxs":       self.feature_maxs,
            "missing_rates":      self.missing_rates,
            "class_balance":      self.class_balance,
            "has_timestamps":     self.has_timestamps,
            "time_range":         list(self.time_range) if self.time_range else None,
        }
