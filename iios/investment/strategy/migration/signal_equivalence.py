"""iios/investment/strategy/migration/signal_equivalence.py
Signal equivalence checking between legacy metadata and adapter output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.migration.legacy_metadata import LegacyStrategyMetadata
from iios.investment.strategy.migration.strategy_adapter import LegacyStrategyAdapter
from iios.investment.strategy.migration.signal_comparator import SignalComparator


_EQUIVALENCE_THRESHOLD = 0.90   # 90% field match required for equivalence
_FLOAT_TOLERANCE       = 1e-6


@dataclass(frozen=True)
class EquivalenceResult:
    """Result of a signal equivalence check between legacy and adapted strategy."""
    strategy_id:    str
    strategy_name:  str
    is_equivalent:  bool
    match_rate:     float
    failed_fields:  List[str]
    total_checks:   int
    passed_checks:  int
    confidence:     float       # 0–100
    summary:        str
    checked_at:     datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":   self.strategy_id,
            "strategy_name": self.strategy_name,
            "is_equivalent": self.is_equivalent,
            "match_rate":    round(self.match_rate, 4),
            "failed_fields": self.failed_fields,
            "total_checks":  self.total_checks,
            "passed_checks": self.passed_checks,
            "confidence":    round(self.confidence, 2),
            "summary":       self.summary,
            "checked_at":    self.checked_at.isoformat(),
        }


class SignalEquivalenceChecker:
    """
    Verifies that a LegacyStrategyAdapter preserves the signal contract
    of the underlying LegacyStrategyMetadata.

    Checks:
    1. Numeric parameter fidelity (tolerance 1e-6)
    2. Direction and category preservation
    3. Entry condition evaluation equivalence (if conditions present)
    """

    def __init__(self, tolerance: float = _FLOAT_TOLERANCE) -> None:
        self._tolerance  = tolerance
        self._comparator = SignalComparator()

    def check(
        self,
        metadata: LegacyStrategyMetadata,
        adapter:  LegacyStrategyAdapter,
        test_cases: Optional[List[Dict[str, float]]] = None,
    ) -> EquivalenceResult:
        """
        Check signal equivalence.

        Args:
            metadata:   Original legacy strategy metadata.
            adapter:    Adapter wrapping the same strategy.
            test_cases: Optional list of feature dicts to evaluate entry conditions.

        Returns:
            EquivalenceResult with detailed findings.
        """
        failures: List[str] = []

        # ── 1. Parameter fidelity ─────────────────────────────────────────────
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

        comparison = self._comparator.compare(
            strategy_id=metadata.strategy_id,
            strategy_name=metadata.strategy_name,
            legacy_params=legacy_params,
            adapted_params=adapted_params,
            tolerance=self._tolerance,
        )
        failures.extend(comparison.mismatched_fields)

        # ── 2. Entry condition equivalence ────────────────────────────────────
        entry_tests_run  = 0
        entry_tests_pass = 0
        if metadata.entry_conditions and test_cases:
            for tc in test_cases:
                legacy_result  = metadata.evaluate_entry_conditions(tc)
                adapted_result = adapter.evaluate_entry(tc)
                entry_tests_run += 1
                if legacy_result == adapted_result:
                    entry_tests_pass += 1
                else:
                    failures.append(
                        f"entry_condition_mismatch(legacy={legacy_result}, adapted={adapted_result})"
                    )

        # ── Aggregate ─────────────────────────────────────────────────────────
        total_checks  = len(comparison.field_comparisons) + entry_tests_run
        passed_checks = sum(1 for c in comparison.field_comparisons if c.match) + entry_tests_pass
        match_rate    = passed_checks / total_checks if total_checks > 0 else 1.0
        is_equivalent = match_rate >= _EQUIVALENCE_THRESHOLD and len(failures) == 0

        # Confidence = weighted: params 70%, entry conditions 30%
        param_conf  = comparison.match_rate * 70
        entry_conf  = (entry_tests_pass / entry_tests_run * 30) if entry_tests_run > 0 else 30.0
        confidence  = round(param_conf + entry_conf, 2)

        summary = (
            f"Equivalent: {passed_checks}/{total_checks} checks passed "
            f"({match_rate:.0%}), confidence={confidence:.0f}"
            if is_equivalent else
            f"Not equivalent: {len(failures)} failures — {', '.join(failures[:3])}"
        )

        return EquivalenceResult(
            strategy_id=metadata.strategy_id,
            strategy_name=metadata.strategy_name,
            is_equivalent=is_equivalent,
            match_rate=round(match_rate, 4),
            failed_fields=failures,
            total_checks=total_checks,
            passed_checks=passed_checks,
            confidence=confidence,
            summary=summary,
            checked_at=datetime.now(timezone.utc),
        )
