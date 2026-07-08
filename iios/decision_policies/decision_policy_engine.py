"""iios/decision_policies/decision_policy_engine.py — Top-level engine gateway."""
from __future__ import annotations

import asyncio
import threading
import time

from .compliance.compliance_policy import CompliancePolicy
from .constraints.constraint import Constraint
from .evaluation.policy_evaluator import PolicyEvaluationResult
from .policy_constants import (
    EvaluationMode,
    POLICY_ENGINE_SYSTEM_ID,
    POLICY_ENGINE_VERSION,
)
from .policy_context import EvaluationContext
from .policy_exceptions import EngineAlreadyRunningError, EngineNotInitializedError
from .policy_manager import PolicyManager, get_policy_manager
from .rules.rule import Rule
from .rules.rule_group import RuleGroup


class DecisionPolicyEngine:
    """
    Top-level gateway for the Decision Policy & Rule Engine.
    No decision may proceed to execution without being evaluated by this engine.
    All policy registrations and evaluations flow through this class.
    """

    VERSION   = POLICY_ENGINE_VERSION
    SYSTEM_ID = POLICY_ENGINE_SYSTEM_ID

    def __init__(self) -> None:
        self._manager:    PolicyManager | None = None
        self._running:    bool                 = False
        self._start_time: float | None         = None
        self._lock        = threading.RLock()

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def initialize(self, manager: PolicyManager | None = None) -> None:
        with self._lock:
            if self._running:
                raise EngineAlreadyRunningError()
            self._manager    = manager or get_policy_manager()
            self._running    = True
            self._start_time = time.time()

    def shutdown(self) -> None:
        with self._lock:
            self._running    = False
            self._start_time = None

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Registration ───────────────────────────────────────────────────────

    def register_rule(self, rule: Rule, *, overwrite: bool = False) -> None:
        self._mgr().register_rule(rule, overwrite=overwrite)

    def register_rule_group(self, group: RuleGroup, *, overwrite: bool = False) -> None:
        self._mgr().register_rule_group(group, overwrite=overwrite)

    def register_constraint(self, constraint: Constraint, *, overwrite: bool = False) -> None:
        self._mgr().register_constraint(constraint, overwrite=overwrite)

    def register_compliance_policy(
        self,
        policy:    CompliancePolicy,
        *,
        overwrite: bool = False,
    ) -> None:
        self._mgr().register_compliance_policy(policy, overwrite=overwrite)

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
    ) -> PolicyEvaluationResult:
        return self._mgr().evaluate(
            context             = context,
            rules               = rules,
            rule_groups         = rule_groups,
            constraints         = constraints,
            compliance_policies = compliance_policies,
            mode                = mode,
        )

    async def evaluate_async(
        self,
        context:             EvaluationContext,
        *,
        rules:               list[Rule]             | None = None,
        rule_groups:         list[RuleGroup]        | None = None,
        constraints:         list[Constraint]       | None = None,
        compliance_policies: list[CompliancePolicy] | None = None,
        mode:                EvaluationMode                = EvaluationMode.LENIENT,
    ) -> PolicyEvaluationResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.evaluate(
                context,
                rules               = rules,
                rule_groups         = rule_groups,
                constraints         = constraints,
                compliance_policies = compliance_policies,
                mode                = mode,
            ),
        )

    def evaluate_all(
        self,
        context: EvaluationContext,
        *,
        mode: EvaluationMode = EvaluationMode.LENIENT,
    ) -> PolicyEvaluationResult:
        """Evaluate all registered policies against a context."""
        return self._mgr().evaluate_all_registered(context, mode=mode)

    # ── Introspection ──────────────────────────────────────────────────────

    def stats(self) -> dict:
        base: dict = {
            "engine_version": self.VERSION,
            "system_id":      self.SYSTEM_ID,
            "is_running":     self._running,
        }
        if self._running and self._manager is not None:
            base.update(self._manager.stats())
            if self._start_time is not None:
                base["uptime_s"] = time.time() - self._start_time
        return base

    def health(self) -> dict:
        if not self._running:
            return {"status": "stopped", "engine_version": self.VERSION}
        s = self.stats()
        return {
            "status":            "healthy",
            "engine_version":    self.VERSION,
            "total_rules":       s.get("total_rules", 0),
            "total_constraints": s.get("total_constraints", 0),
            "total_compliance":  s.get("total_compliance", 0),
        }

    # ── Private ────────────────────────────────────────────────────────────

    def _mgr(self) -> PolicyManager:
        if not self._running or self._manager is None:
            raise EngineNotInitializedError()
        return self._manager


# ── Module-level singleton ────────────────────────────────────────────────────

_engine: DecisionPolicyEngine | None = None
_engine_lock = threading.Lock()


def get_decision_policy_engine() -> DecisionPolicyEngine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = DecisionPolicyEngine()
    return _engine


def reset_decision_policy_engine() -> None:
    global _engine
    with _engine_lock:
        _engine = None
