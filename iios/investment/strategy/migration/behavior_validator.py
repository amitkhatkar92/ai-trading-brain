"""iios/investment/strategy/migration/behavior_validator.py
Behavior equivalence validation using feature-level test cases.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.migration.legacy_metadata import LegacyStrategyMetadata
from iios.investment.strategy.migration.strategy_adapter import LegacyStrategyAdapter


_DEFAULT_PASS_THRESHOLD = 0.90   # 90% of test cases must match


@dataclass
class BehaviorTestCase:
    """
    A single feature vector + expected outputs for behavior testing.
    Set expected_entry_result to None to skip entry evaluation.
    """
    test_id:               str
    features:              Dict[str, float]
    expected_entry_result: Optional[bool] = None
    expected_regime:       Optional[str]  = None
    description:           str            = ""


@dataclass(frozen=True)
class BehaviorCaseResult:
    """Result of running one test case."""
    test_id:        str
    passed:         bool
    legacy_entry:   Optional[bool]
    adapted_entry:  Optional[bool]
    entry_match:    bool
    failure_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id":       self.test_id,
            "passed":        self.passed,
            "legacy_entry":  self.legacy_entry,
            "adapted_entry": self.adapted_entry,
            "entry_match":   self.entry_match,
            "reason":        self.failure_reason,
        }


@dataclass(frozen=True)
class BehaviorReport:
    """
    Summary of all behavior test case executions for one strategy migration.
    """
    strategy_id:     str
    strategy_name:   str
    test_case_count: int
    passed:          int
    failed:          int
    skipped:         int
    pass_rate:       float
    is_equivalent:   bool
    threshold:       float
    case_results:    List[BehaviorCaseResult]
    generated_at:    datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":     self.strategy_id,
            "strategy_name":   self.strategy_name,
            "test_case_count": self.test_case_count,
            "passed":          self.passed,
            "failed":          self.failed,
            "skipped":         self.skipped,
            "pass_rate":       round(self.pass_rate, 4),
            "is_equivalent":   self.is_equivalent,
            "threshold":       self.threshold,
            "generated_at":    self.generated_at.isoformat(),
            "cases":           [r.to_dict() for r in self.case_results],
        }


class BehaviorValidator:
    """
    Validates behavior equivalence between a legacy strategy and its adapter
    by running parameterised test cases.
    """

    def __init__(self, pass_threshold: float = _DEFAULT_PASS_THRESHOLD) -> None:
        self._threshold = pass_threshold

    def validate(
        self,
        metadata:   LegacyStrategyMetadata,
        adapter:    LegacyStrategyAdapter,
        test_cases: List[BehaviorTestCase],
    ) -> BehaviorReport:
        """
        Run all test cases and return a BehaviorReport.
        If no test_cases are provided, returns a trivially-passing report.
        """
        if not test_cases:
            return BehaviorReport(
                strategy_id=metadata.strategy_id,
                strategy_name=metadata.strategy_name,
                test_case_count=0,
                passed=0,
                failed=0,
                skipped=0,
                pass_rate=1.0,
                is_equivalent=True,
                threshold=self._threshold,
                case_results=[],
                generated_at=datetime.now(timezone.utc),
            )

        case_results: List[BehaviorCaseResult] = []
        passed = failed = skipped = 0

        for tc in test_cases:
            result = self._run_case(metadata, adapter, tc)
            case_results.append(result)
            if result.passed:
                passed += 1
            elif tc.expected_entry_result is None:
                skipped += 1
            else:
                failed += 1

        total    = len(test_cases)
        runnable = total - skipped
        rate     = passed / runnable if runnable > 0 else 1.0

        return BehaviorReport(
            strategy_id=metadata.strategy_id,
            strategy_name=metadata.strategy_name,
            test_case_count=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            pass_rate=round(rate, 4),
            is_equivalent=rate >= self._threshold,
            threshold=self._threshold,
            case_results=case_results,
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _run_case(
        metadata: LegacyStrategyMetadata,
        adapter:  LegacyStrategyAdapter,
        tc:       BehaviorTestCase,
    ) -> BehaviorCaseResult:
        """Execute a single test case and compare legacy vs adapter outputs."""
        if tc.expected_entry_result is None and not metadata.entry_conditions:
            return BehaviorCaseResult(
                test_id=tc.test_id,
                passed=True,
                legacy_entry=None,
                adapted_entry=None,
                entry_match=True,
                failure_reason="",
            )

        # Evaluate entry conditions
        legacy_entry  = metadata.evaluate_entry_conditions(tc.features)
        adapted_entry = adapter.evaluate_entry(tc.features)
        entry_match   = legacy_entry == adapted_entry

        passed  = entry_match
        reason  = ""
        if not entry_match:
            reason = (
                f"entry mismatch: legacy={legacy_entry} adapted={adapted_entry}"
            )

        return BehaviorCaseResult(
            test_id=tc.test_id,
            passed=passed,
            legacy_entry=legacy_entry,
            adapted_entry=adapted_entry,
            entry_match=entry_match,
            failure_reason=reason,
        )
