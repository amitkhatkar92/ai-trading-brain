"""iios/decision_policies/policy_manager.py — Policy lifecycle manager."""
from __future__ import annotations

import threading

from .compliance.compliance_engine import ComplianceEngine
from .compliance.compliance_policy import CompliancePolicy
from .constraints.constraint import Constraint
from .constraints.constraint_engine import ConstraintEngine
from .evaluation.policy_evaluator import (
    PolicyEvaluationRequest,
    PolicyEvaluationResult,
    PolicyEvaluator,
)
from .policy_constants import EvaluationMode
from .policy_context import EvaluationContext
from .registry.policy_registry import PolicyRegistry, get_policy_registry
from .rules.rule import Rule
from .rules.rule_engine import RuleEngine
from .rules.rule_group import RuleGroup


class PolicyManager:
    """
    Manages policy lifecycle: registration, configuration, and evaluation dispatch.
    Single entry point for all policy interactions below the engine layer.
    """

    def __init__(self, registry: PolicyRegistry | None = None) -> None:
        self._registry    = registry or get_policy_registry()
        self._rule_engine = RuleEngine()
        self._con_engine  = ConstraintEngine()
        self._comp_engine = ComplianceEngine()
        self._evaluator   = PolicyEvaluator(
            rule_engine       = self._rule_engine,
            constraint_engine = self._con_engine,
            compliance_engine = self._comp_engine,
        )
        self._lock = threading.RLock()

    # ── Registration ───────────────────────────────────────────────────────

    def register_rule(self, rule: Rule, *, overwrite: bool = False) -> None:
        self._registry.register_rule(rule, overwrite=overwrite)

    def register_rule_group(self, group: RuleGroup, *, overwrite: bool = False) -> None:
        self._registry.register_group(group, overwrite=overwrite)

    def register_constraint(self, constraint: Constraint, *, overwrite: bool = False) -> None:
        self._registry.register_constraint(constraint, overwrite=overwrite)

    def register_compliance_policy(
        self,
        policy:    CompliancePolicy,
        *,
        overwrite: bool = False,
    ) -> None:
        self._registry.register_compliance(policy, overwrite=overwrite)
        with self._lock:
            # Also register in the compliance engine for evaluate_all_registered
            self._comp_engine.register(policy)

    # ── Evaluation ─────────────────────────────────────────────────────────

    def evaluate(
        self,
        context:             EvaluationContext,
        *,
        rules:               list[Rule]             | None = None,
        rule_groups:         list[RuleGroup]        | None = None,
        constraints:         list[Constraint]       | None = None,
        compliance_policies: list[CompliancePolicy] | None = None,
        mode:                EvaluationMode                = EvaluationMode.LENIENT,
        source_id:           str                           = "",
    ) -> PolicyEvaluationResult:
        request = PolicyEvaluationRequest(
            source_id        = source_id or context.source_id,
            context          = context,
            rules            = rules or [],
            rule_groups      = rule_groups or [],
            constraints      = constraints or [],
            compliance_pols  = compliance_policies or [],
            evaluation_mode  = mode,
        )
        return self._evaluator.evaluate(request)

    def evaluate_all_registered(
        self,
        context: EvaluationContext,
        *,
        mode:    EvaluationMode = EvaluationMode.LENIENT,
    ) -> PolicyEvaluationResult:
        """Evaluate all registered policy artefacts against a context."""
        return self.evaluate(
            context             = context,
            rules               = self._registry.all_rules(),
            rule_groups         = self._registry.all_groups(),
            constraints         = self._registry.all_constraints(),
            compliance_policies = self._registry.all_compliance(),
            mode                = mode,
        )

    # ── Query ──────────────────────────────────────────────────────────────

    def get_rule(self, rule_id: str) -> Rule:
        return self._registry.get_rule(rule_id)

    def get_constraint(self, constraint_id: str) -> Constraint:
        return self._registry.get_constraint(constraint_id)

    def get_compliance_policy(self, policy_id: str) -> CompliancePolicy:
        return self._registry.get_compliance(policy_id)

    def stats(self) -> dict:
        return self._registry.stats()


# ── Module-level singleton ────────────────────────────────────────────────────

_manager: PolicyManager | None = None
_manager_lock = threading.Lock()


def get_policy_manager() -> PolicyManager:
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = PolicyManager()
    return _manager


def reset_policy_manager() -> None:
    global _manager
    with _manager_lock:
        _manager = None
