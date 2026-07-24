"""
knowledge_policy_chain.py — iios.knowledge.policies
-----------------------------------------------------
KnowledgePolicyChain — chains multiple policies for composite evaluation.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import GovernanceDecision, PolicyChainMode
from .knowledge_policy_context import GovernancePolicyContext
from .knowledge_policy_result import PolicyEvaluationResult

if TYPE_CHECKING:
    from .knowledge_policy import KnowledgePolicy
    from .knowledge_policy_evaluator import KnowledgePolicyEvaluator

_log = get_logger(__name__)


@dataclass(frozen=True)
class ChainResult:
    """Aggregated result of a policy chain evaluation."""
    chain_id:           str
    chain_name:         str
    decision:           GovernanceDecision
    policy_results:     tuple               # Tuple[PolicyEvaluationResult]
    conflicts_resolved: int
    evaluated_count:    int
    reason:             str
    evaluated_at:       str                 # ISO-8601

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id":           self.chain_id,
            "chain_name":         self.chain_name,
            "decision":           self.decision.value,
            "policy_results":     [r.to_dict() for r in self.policy_results],
            "conflicts_resolved": self.conflicts_resolved,
            "evaluated_count":    self.evaluated_count,
            "reason":             self.reason,
            "evaluated_at":       self.evaluated_at,
        }


class KnowledgePolicyChain:
    """
    A named chain of governance policies evaluated together.

    Evaluation Modes
    ----------------
    SEQUENTIAL / COMPOSITE / NESTED / CONDITIONAL:
        Evaluate policies in registration order.  Stop immediately on
        BLOCKED or REJECTED (fail-fast).
    PRIORITY:
        Sort policies by priority (lower integer = higher priority) then
        evaluate sequentially with fail-fast.
    PARALLEL:
        Evaluate ALL policies regardless of intermediate results.
    """

    def __init__(
        self,
        *,
        chain_id:  str                        = "",
        name:      str,
        mode:      PolicyChainMode            = PolicyChainMode.SEQUENTIAL,
        policies:  Optional[List["KnowledgePolicy"]] = None,
        metadata:  Optional[Dict[str, Any]]   = None,
    ) -> None:
        self._chain_id  = chain_id or f"chain-{uuid.uuid4().hex[:10]}"
        self._name      = name
        self._mode      = mode
        self._policies: List["KnowledgePolicy"] = list(policies or [])
        self._metadata  = dict(metadata or {})

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def chain_id(self) -> str:                       return self._chain_id
    @property
    def name(self) -> str:                           return self._name
    @property
    def mode(self) -> PolicyChainMode:               return self._mode
    @property
    def policies(self) -> List["KnowledgePolicy"]:   return list(self._policies)
    @property
    def policy_count(self) -> int:                   return len(self._policies)

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def add_policy(self, policy: "KnowledgePolicy") -> None:
        self._policies.append(policy)

    def remove_policy(self, policy_id: str) -> bool:
        before = len(self._policies)
        self._policies = [p for p in self._policies if p.policy_id != policy_id]
        return len(self._policies) < before

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        artifacts: Dict[str, Any],
        context:   GovernancePolicyContext,
        evaluator: "KnowledgePolicyEvaluator",
    ) -> ChainResult:
        """
        Evaluate all active policies in this chain.

        Returns ChainResult.  Never raises.
        """
        from .knowledge_policy_priority import PolicyPriorityResolver

        ordered = self._ordered_policies()
        results: List[PolicyEvaluationResult] = []
        stop_early = self._mode in (
            PolicyChainMode.SEQUENTIAL,
            PolicyChainMode.COMPOSITE,
            PolicyChainMode.NESTED,
            PolicyChainMode.CONDITIONAL,
            PolicyChainMode.PRIORITY,
        )

        for policy in ordered:
            if not policy.is_active:
                continue
            result = evaluator.evaluate(policy, artifacts, context)
            results.append(result)
            if stop_early and result.decision in (
                GovernanceDecision.BLOCKED,
                GovernanceDecision.REJECTED,
            ):
                _log.debug(
                    f"Chain early stop: chain_id={self._chain_id!r} "
                    f"policy_id={policy.policy_id!r} "
                    f"decision={result.decision.value!r}"
                )
                break

        resolver = PolicyPriorityResolver()
        decision, reason = resolver.resolve(results)

        return ChainResult(
            chain_id           = self._chain_id,
            chain_name         = self._name,
            decision           = decision,
            policy_results     = tuple(results),
            conflicts_resolved = max(0, len(results) - 1),
            evaluated_count    = len(results),
            reason             = reason,
            evaluated_at       = datetime.now(tz=timezone.utc).isoformat(),
        )

    def _ordered_policies(self) -> List["KnowledgePolicy"]:
        if self._mode == PolicyChainMode.PRIORITY:
            return sorted(self._policies, key=lambda p: p.priority.value)
        return list(self._policies)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id":     self._chain_id,
            "name":         self._name,
            "mode":         self._mode.value,
            "policies":     [p.policy_id for p in self._policies],
            "policy_count": self.policy_count,
            "metadata":     self._metadata,
        }
