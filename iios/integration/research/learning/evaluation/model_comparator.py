"""evaluation/model_comparator.py — Compare multiple EvaluationReports."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from iios.integration.research.learning.evaluation.evaluation_report import EvaluationReport


@dataclass
class ComparisonResult:
    """Outcome of comparing a set of model versions on a common metric."""
    metric_name:      str
    higher_is_better: bool
    ranking:          list[dict[str, Any]]  # ordered best → worst
    winner_model_id:  str
    winner_version:   str
    winner_value:     float

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name":      self.metric_name,
            "higher_is_better": self.higher_is_better,
            "ranking":          self.ranking,
            "winner_model_id":  self.winner_model_id,
            "winner_version":   self.winner_version,
            "winner_value":     self.winner_value,
        }


class ModelComparator:
    """Compares EvaluationReports on a named metric."""

    def compare(
        self,
        reports:          list[EvaluationReport],
        metric_name:      str,
        higher_is_better: bool = True,
    ) -> ComparisonResult:
        if not reports:
            raise ValueError("No reports to compare")

        scored = [
            {
                "model_id":      r.model_id,
                "model_version": r.model_version,
                "report_id":     r.report_id,
                "value":         r.get_metric(metric_name),
            }
            for r in reports
        ]
        scored.sort(key=lambda x: x["value"], reverse=higher_is_better)
        winner = scored[0]

        return ComparisonResult(
            metric_name      = metric_name,
            higher_is_better = higher_is_better,
            ranking          = scored,
            winner_model_id  = winner["model_id"],
            winner_version   = winner["model_version"],
            winner_value     = winner["value"],
        )
