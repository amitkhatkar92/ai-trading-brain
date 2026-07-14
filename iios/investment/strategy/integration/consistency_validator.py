"""iios/investment/strategy/integration/consistency_validator.py
Runs all rules against an aggregation state and builds a ValidationReport.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.strategy.integration.aggregation_state import StrategyAggregationState
from iios.investment.strategy.integration.aggregation_engine import AggregationEngine
from iios.investment.strategy.integration.conflict_detector import ConflictDetector
from iios.investment.strategy.integration.consistency_rules import (
    RuleRegistry,
    create_default_rule_registry,
)
from iios.investment.strategy.integration.validation_report import (
    ValidationReport,
    build_validation_report,
)


class ConsistencyValidator:
    """
    Orchestrates the full validation pass for one strategy:
    1. Runs all consistency rules via ConflictDetector
    2. Computes completeness via AggregationEngine
    3. Assembles a ValidationReport
    """

    def __init__(
        self,
        rule_registry:    Optional[RuleRegistry] = None,
        aggregation_engine: Optional[AggregationEngine] = None,
    ) -> None:
        self._detector = ConflictDetector(rule_registry)
        self._engine   = aggregation_engine or AggregationEngine()

    def validate(
        self,
        state:    StrategyAggregationState,
        warnings: Optional[List[str]] = None,
    ) -> ValidationReport:
        check_results  = self._detector.detect(state)
        completeness   = self._engine.completeness(state.strategy_id)

        # Stale warnings
        stale = self._engine.stale_sources(state.strategy_id)
        all_warnings = list(warnings or [])
        if stale:
            all_warnings.append(
                f"Stale sources: {', '.join(s.value for s in stale)}"
            )

        return build_validation_report(
            strategy_id=state.strategy_id,
            check_results=check_results,
            completeness=completeness,
            warnings=all_warnings,
        )

    def register_rule(self, rule) -> None:
        self._detector.register_rule(rule)
