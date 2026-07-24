"""
integration_policy_chain.py — iios.integration.policies
---------------------------------------------------------
IntegrationPolicyChain — chains multiple governance policies
for sequential, parallel, composite, nested, conditional, or
priority-based evaluation.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .constants import PRIORITY_RANK, ConflictResolutionStrategy, PolicyAction, PolicyChainMode
from .integration_policy import IntegrationPolicy
from .integration_policy_context import IntegrationPolicyContext
from .integration_policy_evaluator import IntegrationPolicyEvaluator
from .integration_policy_priority import IntegrationPolicyPriority
from .integration_policy_result import GovernanceDecision, IntegrationPolicyResult


@dataclass
class ChainExecution:
    """Mutable record of a single chain evaluation run."""
    execution_id:  str
    chain_id:      str
    chain_mode:    PolicyChainMode
    started_at:    str
    completed_at:  Optional[str]
    results:       List[IntegrationPolicyResult]
    decision:      Optional[GovernanceDecision]
    success:       bool
    error_message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id":  self.execution_id,
            "chain_id":      self.chain_id,
            "chain_mode":    self.chain_mode.value,
            "started_at":    self.started_at,
            "completed_at":  self.completed_at,
            "results":       [r.to_dict() for r in self.results],
            "decision":      self.decision.to_dict() if self.decision else None,
            "success":       self.success,
            "error_message": self.error_message,
        }


class IntegrationPolicyChain:
    """
    A chain of governance policies evaluated according to a specified mode.

    Modes:
    - SEQUENTIAL  — evaluate one by one; stop on first blocking action.
    - PARALLEL    — evaluate all; aggregate results.
    - COMPOSITE   — evaluate all using CRITICAL_OVERRIDES_ALL resolution.
    - NESTED      — same as PARALLEL for leaf chains (sub-chains composed externally).
    - CONDITIONAL — evaluate only when a predicate function returns True.
    - PRIORITY    — sort policies by priority before sequential evaluation.
    """

    def __init__(
        self,
        chain_id:  Optional[str]                                        = None,
        name:      str                                                   = "default-chain",
        mode:      PolicyChainMode                                       = PolicyChainMode.SEQUENTIAL,
        policies:  Optional[List[IntegrationPolicy]]                    = None,
        evaluator: Optional[IntegrationPolicyEvaluator]                 = None,
        resolver:  Optional[IntegrationPolicyPriority]                  = None,
        condition: Optional[Callable[[IntegrationPolicyContext], bool]]  = None,
    ) -> None:
        self._chain_id  = chain_id or f"chain-{uuid.uuid4().hex[:12]}"
        self._name      = name
        self._mode      = mode
        self._policies  = list(policies or [])
        self._resolver  = resolver  or IntegrationPolicyPriority()
        self._evaluator = evaluator or IntegrationPolicyEvaluator(self._resolver)
        self._condition = condition   # used only in CONDITIONAL mode

    # ── properties ────────────────────────────────────────────────────

    @property
    def chain_id(self)    -> str:             return self._chain_id
    @property
    def name(self)        -> str:             return self._name
    @property
    def mode(self)        -> PolicyChainMode: return self._mode
    @property
    def policy_count(self) -> int:            return len(self._policies)

    def add_policy(self, policy: IntegrationPolicy) -> None:
        self._policies.append(policy)

    # ── execution ─────────────────────────────────────────────────────

    def execute(self, policy_context: IntegrationPolicyContext) -> ChainExecution:
        """Execute the chain and return a ChainExecution record."""
        execution = ChainExecution(
            execution_id  = f"cexec-{uuid.uuid4().hex[:10]}",
            chain_id      = self._chain_id,
            chain_mode    = self._mode,
            started_at    = datetime.now(timezone.utc).isoformat(),
            completed_at  = None,
            results       = [],
            decision      = None,
            success       = False,
            error_message = "",
        )
        try:
            dispatch = {
                PolicyChainMode.SEQUENTIAL:  self._run_sequential,
                PolicyChainMode.PARALLEL:    self._run_parallel,
                PolicyChainMode.COMPOSITE:   self._run_composite,
                PolicyChainMode.NESTED:      self._run_parallel,
                PolicyChainMode.CONDITIONAL: self._run_conditional,
                PolicyChainMode.PRIORITY:    self._run_priority,
            }
            handler = dispatch.get(self._mode, self._run_sequential)
            handler(policy_context, execution)
            execution.success = True
        except Exception as exc:
            execution.error_message = str(exc)
            execution.success       = False

        execution.completed_at = datetime.now(timezone.utc).isoformat()
        return execution

    # ── evaluation modes ──────────────────────────────────────────────

    def _run_sequential(
        self,
        policy_context: IntegrationPolicyContext,
        execution:      ChainExecution,
    ) -> None:
        for policy in self._policies:
            result = self._evaluator.evaluate_single(policy, policy_context)
            execution.results.append(result)
            if result.is_blocking:
                break   # short-circuit on first block
        self._finalise(policy_context, execution, self._policies)

    def _run_parallel(
        self,
        policy_context: IntegrationPolicyContext,
        execution:      ChainExecution,
    ) -> None:
        for policy in self._policies:
            result = self._evaluator.evaluate_single(policy, policy_context)
            execution.results.append(result)
        self._finalise(policy_context, execution, self._policies)

    def _run_composite(
        self,
        policy_context: IntegrationPolicyContext,
        execution:      ChainExecution,
    ) -> None:
        composite_resolver = IntegrationPolicyPriority(
            ConflictResolutionStrategy.CRITICAL_OVERRIDES_ALL
        )
        for policy in self._policies:
            result = self._evaluator.evaluate_single(policy, policy_context)
            execution.results.append(result)
        final_action = composite_resolver.resolve(execution.results, self._policies)
        execution.decision = GovernanceDecision.create(
            request_id     = policy_context.engine_request_id,
            final_action   = final_action,
            policy_results = execution.results,
        )

    def _run_conditional(
        self,
        policy_context: IntegrationPolicyContext,
        execution:      ChainExecution,
    ) -> None:
        if self._condition is not None and not self._condition(policy_context):
            # Condition not met — skip evaluation, auto-approve
            execution.decision = GovernanceDecision.create(
                request_id     = policy_context.engine_request_id,
                final_action   = PolicyAction.APPROVE,
                policy_results = [],
            )
            return
        self._run_parallel(policy_context, execution)

    def _run_priority(
        self,
        policy_context: IntegrationPolicyContext,
        execution:      ChainExecution,
    ) -> None:
        sorted_policies = sorted(
            self._policies,
            key=lambda p: PRIORITY_RANK.get(p.priority, 0),
            reverse=True,
        )
        for policy in sorted_policies:
            result = self._evaluator.evaluate_single(policy, policy_context)
            execution.results.append(result)
            if result.is_blocking:
                break
        self._finalise(policy_context, execution, sorted_policies)

    def _finalise(
        self,
        policy_context: IntegrationPolicyContext,
        execution:      ChainExecution,
        policies:       List[IntegrationPolicy],
    ) -> None:
        final_action   = self._resolver.resolve(execution.results, policies)
        execution.decision = GovernanceDecision.create(
            request_id     = policy_context.engine_request_id,
            final_action   = final_action,
            policy_results = execution.results,
        )
