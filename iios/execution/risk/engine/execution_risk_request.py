"""iios/execution/risk/engine/execution_risk_request.py
==================================================
Request types for the Execution Risk Engine.

Also defines:
  * RuleResult  — result produced by a single risk rule
  * RiskRuleProtocol — structural protocol that all M3+ rules must satisfy

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from iios.execution.risk.lifecycle import RiskCategory

from .constants import OperationType, RuleOutcome


# ── RuleResult ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RuleResult:
    """
    Immutable result produced by a single risk rule evaluation.

    Created by each rule's ``evaluate()`` method and collected by the engine
    during the EVALUATING phase.
    """

    rule_name:     str
    rule_category: str          # RiskCategory.value of the rule
    outcome:       RuleOutcome
    message:       str
    elapsed_ms:    float
    metadata:      Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def passed(self) -> bool:
        return self.outcome in {RuleOutcome.PASSED, RuleOutcome.SKIPPED}

    @property
    def blocked(self) -> bool:
        return self.outcome == RuleOutcome.BLOCKED

    @property
    def warned(self) -> bool:
        return self.outcome == RuleOutcome.WARNING

    @property
    def errored(self) -> bool:
        return self.outcome == RuleOutcome.ERROR

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "rule_name":     self.rule_name,
            "rule_category": self.rule_category,
            "outcome":       self.outcome.value,
            "message":       self.message,
            "elapsed_ms":    self.elapsed_ms,
            "metadata":      dict(self.metadata),
        }


# ── RiskRuleProtocol ──────────────────────────────────────────────────────────

@runtime_checkable
class RiskRuleProtocol(Protocol):
    """
    Structural protocol that every risk rule must satisfy.

    Rules implementing this protocol can be registered with the engine.
    The engine calls ``is_applicable`` before ``evaluate`` to filter rules.

    Non-responsibilities
    --------------------
    * Rules MUST NOT communicate with brokers.
    * Rules MUST NOT execute orders.
    * Rules MUST NOT mutate the EvaluationContext.
    """

    @property
    def rule_name(self) -> str:
        """Unique name identifying this rule (e.g. 'exposure_limit_v2')."""
        ...

    @property
    def risk_category(self) -> RiskCategory:
        """The risk category this rule belongs to."""
        ...

    def is_applicable(self, request: "EvaluationRequest") -> bool:
        """
        Return True if this rule should be applied to *request*.

        The engine will skip rules that return False here.
        """
        ...

    def evaluate(
        self,
        request: "EvaluationRequest",
        context: Any,
    ) -> RuleResult:
        """
        Evaluate the risk for *request* and return a ``RuleResult``.

        The engine calls this inside the EVALUATING phase.
        This method MUST NOT raise; return a RuleResult with
        ``outcome=RuleOutcome.ERROR`` on failure.
        """
        ...


# ── Base request ──────────────────────────────────────────────────────────────

@dataclass
class EvaluationRequest:
    """
    Request submitted to the Execution Risk Engine to evaluate risk for
    a single execution.

    Carries all identifiers, snapshots, and risk limits the engine and
    registered rules need to perform the evaluation.
    """

    # Request identity
    request_id:     str  = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str  = ""
    actor:          str  = ""
    created_at:     float = field(default_factory=time.time)

    # Execution identifiers
    execution_id:   str = ""
    order_id:       str = ""
    position_id:    str = ""
    portfolio_id:   str = ""
    strategy_id:    str = ""
    decision_id:    str = ""
    workflow_id:    str = ""

    # Risk category to evaluate
    risk_category:  Optional[RiskCategory] = None

    # Optional external snapshots — passed verbatim to rules
    execution_snapshot: Dict[str, Any] = field(default_factory=dict)
    position_snapshot:  Dict[str, Any] = field(default_factory=dict)

    # Risk limits — passed verbatim to rules
    risk_limits: Dict[str, Any] = field(default_factory=dict)

    # If > 0, the created M1 evaluation expires after this many seconds
    expiry_ttl_seconds: Optional[float] = None

    # Arbitrary metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def operation_type(self) -> OperationType:
        return OperationType.EVALUATE

    @property
    def has_execution_snapshot(self) -> bool:
        return bool(self.execution_snapshot)

    @property
    def has_position_snapshot(self) -> bool:
        return bool(self.position_snapshot)


# ── QueryEvaluationRequest ────────────────────────────────────────────────────

@dataclass
class QueryEvaluationRequest:
    """Request to query existing evaluations from the engine registry."""

    request_id:      str  = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id:  str  = ""
    actor:           str  = ""
    created_at:      float = field(default_factory=time.time)

    # Filters — all are optional; omitted → no filter on that field
    evaluation_id:    str                    = ""
    portfolio_id:     str                    = ""
    strategy_id:      str                    = ""
    execution_id:     str                    = ""
    risk_category:    Optional[RiskCategory] = None
    include_archived: bool                   = False
    limit:            int                    = 100

    @property
    def operation_type(self) -> OperationType:
        return OperationType.QUERY
