"""
portfolio_policy_chain.py — iios.portfolio.policies
====================================================
Policy chain — a named group of PortfolioPolicy objects evaluated
together according to a configurable chain mode.

Chain Modes
-----------
SEQUENTIAL : Policies evaluated in priority order.  If stop_on_block is
             True (default) evaluation stops as soon as a BLOCK action
             is encountered.
PARALLEL :   All policies are evaluated regardless of individual
             outcomes.  Used when full coverage is required.
COMPOSITE :  Combination of nested chains.  Policies from all added
             chains are merged and evaluated as SEQUENTIAL.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_MAX_CHAIN_SIZE,
    PolicyAction,
    PolicyChainMode,
)
from .exceptions import PortfolioPolicyChainError
from .portfolio_policy import PolicyOutcome, PortfolioPolicy


class PolicyChain:
    """
    Named, ordered group of PortfolioPolicy objects.

    Parameters
    ----------
    chain_id :      Unique identifier (auto-generated UUID if omitted/empty).
    name :          Human-readable chain name.
    mode :          How policies in the chain are evaluated.
    stop_on_block : If True in SEQUENTIAL mode, stop evaluation as soon
                    as a BLOCK outcome is produced.
    max_size :      Maximum number of policies allowed in the chain.
    metadata :      Supplementary metadata dict.
    """

    def __init__(
        self,
        chain_id:     str = "",
        name:         str = "",
        *,
        mode:         PolicyChainMode = PolicyChainMode.SEQUENTIAL,
        stop_on_block: bool = True,
        max_size:     int  = DEFAULT_MAX_CHAIN_SIZE,
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> None:
        self._chain_id      = chain_id or str(uuid.uuid4())
        self._name          = name or f"chain-{self._chain_id[:8]}"
        self._mode          = mode
        self._stop_on_block = stop_on_block
        self._max_size      = max_size
        self._metadata      = dict(metadata or {})
        self._policies:  List[PortfolioPolicy] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def chain_id(self) -> str:
        return self._chain_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def mode(self) -> PolicyChainMode:
        return self._mode

    @property
    def stop_on_block(self) -> bool:
        return self._stop_on_block

    @property
    def policy_count(self) -> int:
        return len(self._policies)

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def add_policy(self, policy: PortfolioPolicy) -> None:
        """Add a policy to this chain."""
        if len(self._policies) >= self._max_size:
            raise PortfolioPolicyChainError(
                f"Policy chain '{self._name}' is at capacity ({self._max_size})",
                chain_id = self._chain_id,
            )
        self._policies.append(policy)

    def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy by ID.  Returns True if found and removed."""
        before = len(self._policies)
        self._policies = [p for p in self._policies if p.policy_id != policy_id]
        return len(self._policies) < before

    def merge(self, other: "PolicyChain") -> None:
        """Merge all policies from another chain into this chain."""
        for policy in other._policies:
            self.add_policy(policy)

    def policies(self) -> List[PortfolioPolicy]:
        """Return a copy of the current policy list."""
        return list(self._policies)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, inputs: Dict[str, Any]) -> List[PolicyOutcome]:
        """
        Evaluate all policies in the chain against the inputs dict.

        Returns
        -------
        List[PolicyOutcome]
            One outcome per evaluated policy.

        Chain modes
        -----------
        SEQUENTIAL : Policies evaluated in order of their priority
                     (CRITICAL first).  Stops early on BLOCK if
                     stop_on_block is True.
        PARALLEL :   All policies evaluated regardless of outcomes.
        COMPOSITE :  Treated as SEQUENTIAL (merge is done at add time).
        """
        if not self._policies:
            return []

        # Sort by priority (CRITICAL=0 first)
        sorted_policies = sorted(self._policies, key=lambda p: int(p.priority))

        outcomes: List[PolicyOutcome] = []

        if self._mode == PolicyChainMode.PARALLEL:
            # All policies regardless of outcome
            for policy in sorted_policies:
                outcome = policy.evaluate(inputs)
                outcomes.append(outcome)
        else:
            # SEQUENTIAL / COMPOSITE — evaluate in order, optional early-stop
            for policy in sorted_policies:
                outcome = policy.evaluate(inputs)
                outcomes.append(outcome)
                if self._stop_on_block and outcome.action == PolicyAction.BLOCK:
                    break

        return outcomes

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id":      self._chain_id,
            "name":          self._name,
            "mode":          self._mode.value,
            "stop_on_block": self._stop_on_block,
            "policy_count":  len(self._policies),
            "policy_ids":    [p.policy_id for p in self._policies],
        }

    def __repr__(self) -> str:
        return (
            f"PolicyChain(id={self._chain_id!r}, name={self._name!r}, "
            f"mode={self._mode.value!r}, policies={len(self._policies)})"
        )
