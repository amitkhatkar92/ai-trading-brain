"""iios/investment/strategy/integration/consistency_rules.py
Consistency rule definitions and registry.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.integration.integration_constants import (
    ConflictSeverity,
    ConflictType,
    IntelligenceSource,
)
from iios.investment.strategy.integration.aggregation_state import IntelligenceUpdate


@dataclass(frozen=True)
class RuleCheckResult:
    """Outcome of one consistency rule check."""
    rule_id:        str
    rule_name:      str
    passed:         bool
    conflict_type:  Optional[ConflictType]
    severity:       Optional[ConflictSeverity]
    description:    str
    source_a:       Optional[IntelligenceSource]
    source_b:       Optional[IntelligenceSource]
    checked_at:     datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":       self.rule_id,
            "rule_name":     self.rule_name,
            "passed":        self.passed,
            "conflict_type": self.conflict_type.value if self.conflict_type else None,
            "severity":      self.severity.value if self.severity else None,
            "description":   self.description,
            "source_a":      self.source_a.value if self.source_a else None,
            "source_b":      self.source_b.value if self.source_b else None,
            "checked_at":    self.checked_at.isoformat(),
        }


class ConsistencyRule(ABC):
    """Base class for all consistency rules."""

    @property
    @abstractmethod
    def rule_id(self) -> str: ...

    @property
    @abstractmethod
    def rule_name(self) -> str: ...

    @property
    @abstractmethod
    def required_sources(self) -> Tuple[IntelligenceSource, IntelligenceSource]: ...

    @abstractmethod
    def check(
        self,
        a: IntelligenceUpdate,
        b: IntelligenceUpdate,
    ) -> RuleCheckResult: ...

    def _pass(self) -> RuleCheckResult:
        return RuleCheckResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            passed=True,
            conflict_type=None,
            severity=None,
            description="Consistency check passed.",
            source_a=self.required_sources[0],
            source_b=self.required_sources[1],
            checked_at=datetime.now(timezone.utc),
        )

    def _fail(
        self,
        conflict_type: ConflictType,
        severity:      ConflictSeverity,
        description:   str,
    ) -> RuleCheckResult:
        return RuleCheckResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            passed=False,
            conflict_type=conflict_type,
            severity=severity,
            description=description,
            source_a=self.required_sources[0],
            source_b=self.required_sources[1],
            checked_at=datetime.now(timezone.utc),
        )


# ── Built-in rules ────────────────────────────────────────────────────────────

class EvaluationVsRiskRule(ConsistencyRule):
    """High evaluation score must not conflict with critical risk flags."""

    rule_id   = "R001"
    rule_name = "Evaluation vs Risk"
    required_sources = (IntelligenceSource.EVALUATION, IntelligenceSource.RISK)

    def check(self, a: IntelligenceUpdate, b: IntelligenceUpdate) -> RuleCheckResult:
        eval_score  = float(a.payload.get("score", 50.0))
        risk_level  = str(b.payload.get("risk_level", "medium")).lower()
        if eval_score >= 70 and risk_level == "critical":
            return self._fail(
                ConflictType.EVALUATION_VS_RISK,
                ConflictSeverity.HIGH,
                f"Evaluation score {eval_score:.0f} is HIGH but risk level is CRITICAL.",
            )
        return self._pass()


class OpportunityVsPortfolioRule(ConsistencyRule):
    """Opportunity signals entry but portfolio capacity is exhausted."""

    rule_id   = "R002"
    rule_name = "Opportunity vs Portfolio"
    required_sources = (IntelligenceSource.OPPORTUNITY, IntelligenceSource.PORTFOLIO)

    def check(self, a: IntelligenceUpdate, b: IntelligenceUpdate) -> RuleCheckResult:
        has_opportunity = bool(a.payload.get("has_opportunity", False))
        capacity_pct    = float(b.payload.get("capacity_utilisation_pct", 0.0))
        if has_opportunity and capacity_pct >= 100.0:
            return self._fail(
                ConflictType.OPPORTUNITY_VS_PORTFOLIO,
                ConflictSeverity.MEDIUM,
                "Opportunity detected but portfolio capacity is at 100%.",
            )
        return self._pass()


class LearningVsEvaluationRule(ConsistencyRule):
    """Poor historical win rate contradicts high evaluation score."""

    rule_id   = "R003"
    rule_name = "Learning vs Evaluation"
    required_sources = (IntelligenceSource.LEARNING, IntelligenceSource.EVALUATION)

    def check(self, a: IntelligenceUpdate, b: IntelligenceUpdate) -> RuleCheckResult:
        win_rate    = float(a.payload.get("win_rate", 0.5))
        eval_score  = float(b.payload.get("score", 50.0))
        if win_rate < 0.40 and eval_score >= 65:
            return self._fail(
                ConflictType.LEARNING_VS_EVALUATION,
                ConflictSeverity.MEDIUM,
                f"Win rate {win_rate:.0%} is below 40% but evaluation score is {eval_score:.0f}.",
            )
        return self._pass()


class DebateVsRiskRule(ConsistencyRule):
    """Strong debate support contradicts critical risk intelligence."""

    rule_id   = "R004"
    rule_name = "Debate vs Risk"
    required_sources = (IntelligenceSource.DEBATE, IntelligenceSource.RISK)

    def check(self, a: IntelligenceUpdate, b: IntelligenceUpdate) -> RuleCheckResult:
        consensus   = str(a.payload.get("consensus_level", "")).lower()
        risk_level  = str(b.payload.get("risk_level", "")).lower()
        if consensus in ("unanimous", "strong") and risk_level == "critical":
            return self._fail(
                ConflictType.DEBATE_VS_RISK,
                ConflictSeverity.HIGH,
                f"Debate has {consensus} support but risk level is CRITICAL.",
            )
        return self._pass()


class MigrationVsEvaluationRule(ConsistencyRule):
    """Active migration process contradicts active evaluation scoring."""

    rule_id   = "R005"
    rule_name = "Migration vs Evaluation"
    required_sources = (IntelligenceSource.MIGRATION, IntelligenceSource.EVALUATION)

    def check(self, a: IntelligenceUpdate, b: IntelligenceUpdate) -> RuleCheckResult:
        migration_phase = str(a.payload.get("phase", "")).lower()
        eval_status     = str(b.payload.get("status", "")).lower()
        if migration_phase in ("validating", "rollback") and eval_status == "active":
            return self._fail(
                ConflictType.MIGRATION_VS_EVALUATION,
                ConflictSeverity.MEDIUM,
                f"Migration is in {migration_phase} phase but evaluation marks strategy active.",
            )
        return self._pass()


class PortfolioVsOpportunityRule(ConsistencyRule):
    """Portfolio shows position already open but opportunity signals fresh entry."""

    rule_id   = "R006"
    rule_name = "Portfolio vs Opportunity"
    required_sources = (IntelligenceSource.PORTFOLIO, IntelligenceSource.OPPORTUNITY)

    def check(self, a: IntelligenceUpdate, b: IntelligenceUpdate) -> RuleCheckResult:
        has_open_position = bool(a.payload.get("has_open_position", False))
        signal_type       = str(b.payload.get("signal_type", "")).lower()
        if has_open_position and signal_type == "entry":
            return self._fail(
                ConflictType.PORTFOLIO_VS_OPPORTUNITY,
                ConflictSeverity.LOW,
                "Portfolio already holds an open position but opportunity signals new entry.",
            )
        return self._pass()


class LifecycleVsEvaluationRule(ConsistencyRule):
    """Deprecated/retired lifecycle status contradicts active evaluation."""

    rule_id   = "R007"
    rule_name = "Lifecycle vs Evaluation"
    required_sources = (IntelligenceSource.LIFECYCLE, IntelligenceSource.EVALUATION)

    def check(self, a: IntelligenceUpdate, b: IntelligenceUpdate) -> RuleCheckResult:
        lifecycle_status = str(a.payload.get("status", "")).lower()
        eval_status      = str(b.payload.get("status", "")).lower()
        if lifecycle_status in ("deprecated", "retired", "archived") and eval_status == "active":
            return self._fail(
                ConflictType.LIFECYCLE_VS_EVALUATION,
                ConflictSeverity.HIGH,
                f"Strategy lifecycle is {lifecycle_status} but evaluation marks it active.",
            )
        return self._pass()


# ── Rule registry ─────────────────────────────────────────────────────────────

class RuleRegistry:
    """Registry of all active consistency rules. Supports runtime registration."""

    def __init__(self) -> None:
        self._rules: Dict[str, ConsistencyRule] = {}

    def register(self, rule: ConsistencyRule) -> None:
        self._rules[rule.rule_id] = rule

    def unregister(self, rule_id: str) -> None:
        self._rules.pop(rule_id, None)

    def all(self) -> List[ConsistencyRule]:
        return list(self._rules.values())

    def get(self, rule_id: str) -> Optional[ConsistencyRule]:
        return self._rules.get(rule_id)

    def count(self) -> int:
        return len(self._rules)


def create_default_rule_registry() -> RuleRegistry:
    reg = RuleRegistry()
    for cls in [
        EvaluationVsRiskRule,
        OpportunityVsPortfolioRule,
        LearningVsEvaluationRule,
        DebateVsRiskRule,
        MigrationVsEvaluationRule,
        PortfolioVsOpportunityRule,
        LifecycleVsEvaluationRule,
    ]:
        reg.register(cls())
    return reg
