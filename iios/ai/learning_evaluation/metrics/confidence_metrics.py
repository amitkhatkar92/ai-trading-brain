"""
confidence_metrics.py -- iios.ai.learning_evaluation.metrics
==============================================================
:class:`ConfidenceMetrics` — mean confidence, calibration, overconfidence.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class ConfidenceMetrics:
    """
    Immutable confidence calibration metrics.

    ``calibration_error`` — Expected Calibration Error (ECE), lower is better.
    ``overconfidence_rate`` — fraction of predictions with confidence > actual accuracy.
    ``underconfidence_rate`` — fraction where confidence < actual accuracy.
    """

    metrics_id:          str
    mean_confidence:     float
    calibration_error:   float   # ECE, 0.0–1.0
    overconfidence_rate: float   # 0.0–1.0
    underconfidence_rate: float  # 0.0–1.0
    sample_size:         int
    computed_at:         float

    @classmethod
    def compute(
        cls,
        confidences: List[float],
        outcomes:    List[bool],    # True = correct prediction
    ) -> "ConfidenceMetrics":
        """
        Compute confidence metrics from parallel lists of confidence values and correctness.

        Both lists must have the same length.
        """
        n = min(len(confidences), len(outcomes))
        if n == 0:
            return cls(
                metrics_id           = str(uuid.uuid4()),
                mean_confidence      = 0.0,
                calibration_error    = 0.0,
                overconfidence_rate  = 0.0,
                underconfidence_rate = 0.0,
                sample_size          = 0,
                computed_at          = time.time(),
            )
        confs    = confidences[:n]
        results  = outcomes[:n]
        mean_c   = sum(confs) / n
        # Simple ECE: mean |confidence - accuracy|
        ece      = sum(abs(c - (1.0 if r else 0.0)) for c, r in zip(confs, results)) / n
        over_c   = sum(1 for c, r in zip(confs, results) if c > 0.5 and not r) / n
        under_c  = sum(1 for c, r in zip(confs, results) if c <= 0.5 and r) / n
        return cls(
            metrics_id           = str(uuid.uuid4()),
            mean_confidence      = round(mean_c, 6),
            calibration_error    = round(ece, 6),
            overconfidence_rate  = round(over_c, 6),
            underconfidence_rate = round(under_c, 6),
            sample_size          = n,
            computed_at          = time.time(),
        )

    def is_well_calibrated(self, max_ece: float = 0.1) -> bool:
        return self.calibration_error <= max_ece
