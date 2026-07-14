"""iios/investment/strategy/integration/conflict_detector.py
Detects conflicts between intelligence updates using consistency rules.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.integration.integration_constants import (
    ConflictSeverity,
    ConflictType,
    IntelligenceSource,
)
from iios.investment.strategy.integration.aggregation_state import (
    IntelligenceUpdate,
    StrategyAggregationState,
)
from iios.investment.strategy.integration.consistency_rules import (
    RuleCheckResult,
    RuleRegistry,
    create_default_rule_registry,
)


class ConflictDetector:
    """
    Runs all registered consistency rules against the latest intelligence
    for a strategy and returns failed rule results (i.e., conflicts).
    Stateless — all state is in the passed-in aggregation state.
    """

    def __init__(self, rule_registry: Optional[RuleRegistry] = None) -> None:
        self._rules = rule_registry or create_default_rule_registry()

    def detect(
        self,
        state: StrategyAggregationState,
    ) -> List[RuleCheckResult]:
        """Return all failed rule checks (conflicts) for the strategy."""
        latest   = state.all_latest()
        failures: List[RuleCheckResult] = []

        for rule in self._rules.all():
            src_a, src_b = rule.required_sources
            upd_a = latest.get(src_a)
            upd_b = latest.get(src_b)
            if upd_a is None or upd_b is None:
                continue
            result = rule.check(upd_a, upd_b)
            if not result.passed:
                failures.append(result)

        return failures

    def has_critical_conflict(self, state: StrategyAggregationState) -> bool:
        return any(
            r.severity == ConflictSeverity.CRITICAL
            for r in self.detect(state)
        )

    def register_rule(self, rule) -> None:
        self._rules.register(rule)

    def rule_count(self) -> int:
        return self._rules.count()
