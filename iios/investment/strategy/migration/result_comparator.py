"""iios/investment/strategy/migration/result_comparator.py
Compares overall migration results (parameters + behavior) between legacy and adapted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.migration.legacy_metadata import LegacyStrategyMetadata
from iios.investment.strategy.migration.strategy_adapter import LegacyStrategyAdapter
from iios.investment.strategy.migration.signal_comparator import SignalComparator
from iios.investment.strategy.migration.behavior_validator import (
    BehaviorTestCase,
    BehaviorValidator,
)


_EQUIVALENCE_THRESHOLD = 0.90


@dataclass(frozen=True)
class ComparisonResult:
    """Aggregated comparison result for one strategy migration."""
    strategy_id:          str
    strategy_name:        str
    total_test_cases:     int
    matching_cases:       int
    non_matching_cases:   int
    overall_match_rate:   float
    is_equivalent:        bool
    parameter_deviations: Dict[str, float]
    failed_parameters:    List[str]
    checked_at:           datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":         self.strategy_id,
            "strategy_name":       self.strategy_name,
            "total_test_cases":    self.total_test_cases,
            "matching_cases":      self.matching_cases,
            "non_matching_cases":  self.non_matching_cases,
            "overall_match_rate":  round(self.overall_match_rate, 4),
            "is_equivalent":       self.is_equivalent,
            "parameter_deviations": {
                k: round(v, 6) for k, v in self.parameter_deviations.items()
            },
            "failed_parameters":   self.failed_parameters,
            "checked_at":          self.checked_at.isoformat(),
        }


class ResultComparator:
    """
    High-level comparator that combines signal parameter and behavior comparison.
    Produces a ComparisonResult for reporting and approval decisions.
    """

    def __init__(self, tolerance: float = 1e-6) -> None:
        self._tolerance        = tolerance
        self._signal_comparator = SignalComparator()
        self._behavior_validator = BehaviorValidator()

    def compare(
        self,
        metadata:   LegacyStrategyMetadata,
        adapter:    LegacyStrategyAdapter,
        test_cases: Optional[List[BehaviorTestCase]] = None,
    ) -> ComparisonResult:
        """
        Compare legacy strategy vs adapter across parameters and behavior.

        Args:
            metadata:   Original legacy metadata.
            adapter:    Adapter wrapping the strategy.
            test_cases: Optional behavior test cases.

        Returns:
            ComparisonResult with overall match assessment.
        """
        # ── Signal parameters ─────────────────────────────────────────────────
        legacy_params  = {
            "min_rr":            metadata.min_rr,
            "max_loss_pct":      metadata.max_loss_pct,
            "stop_loss_pct":     metadata.stop_loss_pct,
            "target_multiplier": metadata.target_multiplier,
            "direction":         metadata.direction,
            "category":          metadata.category,
        }
        adapted_params = adapter.get_risk_params()
        adapted_params["direction"] = adapter.metadata.direction
        adapted_params["category"]  = adapter.metadata.category

        signal_cmp = self._signal_comparator.compare(
            strategy_id=metadata.strategy_id,
            strategy_name=metadata.strategy_name,
            legacy_params=legacy_params,
            adapted_params=adapted_params,
            tolerance=self._tolerance,
        )

        param_deviations: Dict[str, float] = {
            fc.field.value: fc.deviation
            for fc in signal_cmp.field_comparisons
            if not fc.match
        }
        failed_params = list(param_deviations.keys())

        # ── Behavior test cases ───────────────────────────────────────────────
        tc_list  = test_cases or []
        total    = len(tc_list)
        matching = 0

        if tc_list:
            report = self._behavior_validator.validate(metadata, adapter, tc_list)
            matching = report.passed
        else:
            matching = 0
            total    = 0

        # ── Combine ───────────────────────────────────────────────────────────
        param_pass  = len(failed_params) == 0
        behavior_ok = (matching >= int(total * _EQUIVALENCE_THRESHOLD)) if total > 0 else True

        # Match rate: weight params 60%, behavior 40%
        param_rate    = signal_cmp.match_rate
        behavior_rate = (matching / total) if total > 0 else 1.0
        combined_rate = param_rate * 0.6 + behavior_rate * 0.4

        return ComparisonResult(
            strategy_id=metadata.strategy_id,
            strategy_name=metadata.strategy_name,
            total_test_cases=total,
            matching_cases=matching,
            non_matching_cases=total - matching,
            overall_match_rate=round(combined_rate, 4),
            is_equivalent=param_pass and behavior_ok,
            parameter_deviations=param_deviations,
            failed_parameters=failed_params,
            checked_at=datetime.now(timezone.utc),
        )
