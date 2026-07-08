"""
iios/intelligence/forecast/evaluation/model_feedback.py
========================================================
ModelFeedback — feeds accuracy results back to models for adaptation.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from .prediction_accuracy import AccuracyReport


@dataclass
class FeedbackRecord:
    """Accumulated feedback for a single model."""

    model_id:    str
    total:       int    = 0
    sum_scores:  float  = 0.0
    worst_score: float  = 1.0
    best_score:  float  = 0.0

    @property
    def average_score(self) -> float:
        return self.sum_scores / self.total if self.total > 0 else 0.0

    def update(self, report: AccuracyReport) -> None:
        self.total      += 1
        self.sum_scores += report.composite
        self.worst_score = min(self.worst_score, report.composite)
        self.best_score  = max(self.best_score,  report.composite)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id":     self.model_id,
            "total":        self.total,
            "average":      round(self.average_score, 4),
            "best":         round(self.best_score, 4),
            "worst":        round(self.worst_score, 4),
        }


class ModelFeedback:
    """
    Collects accuracy reports and makes them available so model owners
    can adjust weights, hyper-parameters, or disable under-performers.

    Does NOT mutate models directly — it only stores diagnostics.
    """

    def __init__(self, underperform_threshold: float = 0.30) -> None:
        self._records:    dict[str, FeedbackRecord] = {}
        self._threshold:  float                      = underperform_threshold
        self._lock:       threading.RLock             = threading.RLock()

    def record(self, model_id: str, report: AccuracyReport) -> None:
        with self._lock:
            if model_id not in self._records:
                self._records[model_id] = FeedbackRecord(model_id=model_id)
            self._records[model_id].update(report)

    def underperforming_models(self) -> list[str]:
        """Return model IDs with average score below threshold."""
        with self._lock:
            return [
                mid for mid, rec in self._records.items()
                if rec.total >= 5 and rec.average_score < self._threshold
            ]

    def get_record(self, model_id: str) -> FeedbackRecord | None:
        with self._lock:
            return self._records.get(model_id)

    def all_records(self) -> list[FeedbackRecord]:
        with self._lock:
            return list(self._records.values())

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "models": len(self._records),
                "underperformers": len(self.underperforming_models()),
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:     threading.Lock          = threading.Lock()
_FEEDBACK: ModelFeedback | None   = None


def get_model_feedback() -> ModelFeedback:
    global _FEEDBACK
    if _FEEDBACK is None:
        with _LOCK:
            if _FEEDBACK is None:
                _FEEDBACK = ModelFeedback()
    return _FEEDBACK


def reset_model_feedback() -> None:
    global _FEEDBACK
    with _LOCK:
        _FEEDBACK = None
