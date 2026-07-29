"""
accuracy_metrics.py -- iios.ai.learning_evaluation.metrics
============================================================
:class:`AccuracyMetrics` — precision, recall, F1, accuracy.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class AccuracyMetrics:
    """Immutable accuracy metrics computed from evaluation results."""

    metrics_id:  str
    precision:   float   # TP / (TP + FP)
    recall:      float   # TP / (TP + FN)
    f1:          float   # harmonic mean of precision and recall
    accuracy:    float   # (TP + TN) / total
    sample_size: int
    computed_at: float

    @classmethod
    def compute(
        cls,
        true_positives:  int,
        false_positives: int,
        false_negatives: int,
        true_negatives:  int,
    ) -> "AccuracyMetrics":
        tp, fp, fn, tn = true_positives, false_positives, false_negatives, true_negatives
        total     = tp + fp + fn + tn
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall    = tp / (tp + fn) if (tp + fn) else 0.0
        f1        = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        accuracy  = (tp + tn) / total if total else 0.0
        return cls(
            metrics_id  = str(uuid.uuid4()),
            precision   = round(precision, 6),
            recall      = round(recall, 6),
            f1          = round(f1, 6),
            accuracy    = round(accuracy, 6),
            sample_size = total,
            computed_at = time.time(),
        )

    @classmethod
    def from_scores(
        cls,
        scores:    list,   # list of float 0.0–1.0
        threshold: float = 0.5,
    ) -> "AccuracyMetrics":
        """Binary accuracy from a list of prediction scores (no ground-truth breakdown)."""
        n = len(scores)
        if not n:
            return cls.compute(0, 0, 0, 0)
        above = sum(1 for s in scores if s >= threshold)
        below = n - above
        # treat above-threshold as pass; no ground truth → TP=above, TN=0, FP=0, FN=below
        return cls.compute(above, 0, below, 0)
