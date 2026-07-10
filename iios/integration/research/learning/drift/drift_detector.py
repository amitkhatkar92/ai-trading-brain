"""drift/drift_detector.py — Statistical drift detection (PSI + mean-shift)."""
from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import (
    DriftType,
    MEAN_SHIFT_THRESHOLD,
    PSI_DRIFT_THRESHOLD,
)
from iios.integration.research.learning.learning_exceptions import DriftDetectedError


@dataclass
class DriftResult:
    """Outcome of a single drift check."""
    result_id:       str
    model_id:        str
    drift_type:      DriftType
    is_drifted:      bool
    drift_score:     float
    threshold:       float
    detail:          dict[str, Any]
    checked_at:      float

    @classmethod
    def create(
        cls,
        model_id:    str,
        drift_type:  DriftType,
        is_drifted:  bool,
        drift_score: float,
        threshold:   float,
        detail:      Optional[dict] = None,
    ) -> "DriftResult":
        return cls(
            result_id   = f"dr_{uuid.uuid4().hex[:10]}",
            model_id    = model_id,
            drift_type  = drift_type,
            is_drifted  = is_drifted,
            drift_score = drift_score,
            threshold   = threshold,
            detail      = detail or {},
            checked_at  = time.time(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":   self.result_id,
            "model_id":    self.model_id,
            "drift_type":  self.drift_type.value,
            "is_drifted":  self.is_drifted,
            "drift_score": self.drift_score,
            "threshold":   self.threshold,
            "detail":      self.detail,
            "checked_at":  self.checked_at,
        }


class DriftDetector:
    """
    Detects data drift and performance drift using PSI and mean-shift methods.

    All computations are pure Python — no external libraries required.
    """

    def __init__(
        self,
        psi_threshold:         float = PSI_DRIFT_THRESHOLD,
        mean_shift_threshold:  float = MEAN_SHIFT_THRESHOLD,
    ) -> None:
        self.psi_threshold        = psi_threshold
        self.mean_shift_threshold = mean_shift_threshold
        self._checks_run          = 0
        self._drifts_detected     = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def check_data_drift(
        self,
        model_id:      str,
        baseline_data: list[dict[str, Any]],
        current_data:  list[dict[str, Any]],
    ) -> DriftResult:
        """Compute PSI across all numeric features and return the worst score."""
        if not baseline_data or not current_data:
            return DriftResult.create(model_id, DriftType.DATA_DRIFT, False, 0.0, self.psi_threshold)

        features = [k for k in baseline_data[0] if isinstance(baseline_data[0][k], (int, float))]
        if not features:
            return DriftResult.create(model_id, DriftType.DATA_DRIFT, False, 0.0, self.psi_threshold)

        psi_scores: dict[str, float] = {}
        for feat in features:
            baseline_vals = [r[feat] for r in baseline_data if isinstance(r.get(feat), (int, float))]
            current_vals  = [r[feat] for r in current_data  if isinstance(r.get(feat), (int, float))]
            if baseline_vals and current_vals:
                psi_scores[feat] = self.psi(baseline_vals, current_vals)

        max_psi    = max(psi_scores.values()) if psi_scores else 0.0
        is_drifted = max_psi > self.psi_threshold
        self._checks_run     += 1
        if is_drifted:
            self._drifts_detected += 1
        return DriftResult.create(
            model_id    = model_id,
            drift_type  = DriftType.DATA_DRIFT,
            is_drifted  = is_drifted,
            drift_score = max_psi,
            threshold   = self.psi_threshold,
            detail      = {"psi_per_feature": psi_scores},
        )

    def check_performance_drift(
        self,
        model_id:         str,
        baseline_metrics: dict[str, float],
        current_metrics:  dict[str, float],
    ) -> DriftResult:
        """
        Detect performance drift by comparing metric values.

        Uses normalised absolute change as drift score.
        """
        common = [k for k in baseline_metrics if k in current_metrics]
        if not common:
            return DriftResult.create(
                model_id, DriftType.PERFORMANCE_DRIFT, False, 0.0, self.psi_threshold
            )

        changes: dict[str, float] = {}
        for k in common:
            base = baseline_metrics[k]
            curr = current_metrics[k]
            changes[k] = abs(curr - base) / (abs(base) + 1e-10)

        max_change = max(changes.values()) if changes else 0.0
        is_drifted = max_change > self.psi_threshold
        self._checks_run += 1
        if is_drifted:
            self._drifts_detected += 1
        return DriftResult.create(
            model_id    = model_id,
            drift_type  = DriftType.PERFORMANCE_DRIFT,
            is_drifted  = is_drifted,
            drift_score = max_change,
            threshold   = self.psi_threshold,
            detail      = {"relative_change_per_metric": changes},
        )

    # ── Algorithms ────────────────────────────────────────────────────────────

    def psi(self, expected: list[float], actual: list[float], n_bins: int = 10) -> float:
        """
        Population Stability Index.

        PSI < 0.10 → no shift
        0.10 ≤ PSI < 0.20 → minor shift
        PSI ≥ 0.20 → significant shift
        """
        if not expected or not actual:
            return 0.0

        lo = min(min(expected), min(actual))
        hi = max(max(expected), max(actual))
        if lo == hi:
            return 0.0

        bin_width = (hi - lo) / n_bins
        edges = [lo + i * bin_width for i in range(n_bins + 1)]
        edges[-1] += 1e-10  # include the max value

        def _bin_fractions(vals: list[float]) -> list[float]:
            counts = [0] * n_bins
            for v in vals:
                for i in range(n_bins):
                    if edges[i] <= v < edges[i + 1]:
                        counts[i] += 1
                        break
            total = len(vals)
            return [max(c / total, 1e-6) for c in counts]

        exp_frac = _bin_fractions(expected)
        act_frac = _bin_fractions(actual)

        return sum(
            (a - e) * math.log(a / e)
            for e, a in zip(exp_frac, act_frac)
        )

    def mean_shift_score(self, baseline: list[float], current: list[float]) -> float:
        """
        Mean-shift in units of baseline standard deviation.

        A score > mean_shift_threshold indicates significant shift.
        """
        if not baseline or not current:
            return 0.0
        base_mean = sum(baseline) / len(baseline)
        base_var  = sum((v - base_mean) ** 2 for v in baseline) / len(baseline)
        base_std  = math.sqrt(base_var) if base_var > 0 else 1.0
        curr_mean = sum(current) / len(current)
        return abs(curr_mean - base_mean) / base_std

    def stats(self) -> dict[str, Any]:
        return {
            "checks_run":       self._checks_run,
            "drifts_detected":  self._drifts_detected,
            "psi_threshold":    self.psi_threshold,
            "mean_shift_threshold": self.mean_shift_threshold,
        }
