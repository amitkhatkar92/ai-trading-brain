"""
market_policy_factory.py — iios.market.policies
=================================================
Factory for creating Market Policy Framework objects with sensible defaults.

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    DEFAULT_POLICY_ACTION,
    VERSION,
    EvaluationMode,
    MarketPolicyType,
    PolicyAction,
    PolicyPriority,
)
from .market_policy import MarketPolicy
from .market_policy_context import MarketPolicyContext
from .market_policy_request import MarketPolicyRequest
from .market_policy_result import MarketPolicyResult
from .market_policy_rule import MarketPolicyRule


class MarketPolicyFactory:
    """
    Convenience factory for constructing Market Policy Framework objects.

    All methods return fully-initialised immutable value objects with
    sensible defaults.  The factory performs no evaluation logic.
    """

    # ------------------------------------------------------------------
    # Context & Request
    # ------------------------------------------------------------------

    def create_context(
        self,
        evaluation_id:      str,
        market_analysis_id: str,
        exchange:           str,
        *,
        source:         str                                       = "",
        policy_types:   Optional[Tuple[MarketPolicyType, ...]]   = None,
        priority_floor: PolicyPriority                            = PolicyPriority.INFORMATIONAL,
        correlation_id: str                                       = "",
        metadata:       Optional[Dict[str, Any]]                  = None,
    ) -> MarketPolicyContext:
        return MarketPolicyContext.create(
            evaluation_id      = evaluation_id,
            market_analysis_id = market_analysis_id,
            exchange           = exchange,
            source             = source,
            policy_types       = policy_types,
            priority_floor     = priority_floor,
            correlation_id     = correlation_id,
            metadata           = metadata,
        )

    def create_request(
        self,
        evaluation_id:      str,
        market_analysis_id: str,
        exchange:           str,
        *,
        inputs:     Optional[Dict[str, Any]]     = None,
        context:    Optional[MarketPolicyContext] = None,
        request_id: Optional[str]                = None,
        metadata:   Optional[Dict[str, Any]]     = None,
    ) -> MarketPolicyRequest:
        return MarketPolicyRequest.create(
            evaluation_id      = evaluation_id,
            market_analysis_id = market_analysis_id,
            exchange           = exchange,
            request_id         = request_id,
            context            = context,
            inputs             = inputs,
            metadata           = metadata,
        )

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------

    def create_simple_policy(
        self,
        name:        str,
        policy_type: MarketPolicyType,
        priority:    PolicyPriority    = PolicyPriority.MEDIUM,
        *,
        default_action: PolicyAction    = DEFAULT_POLICY_ACTION,
        enabled:        bool            = True,
        description:    str             = "",
        policy_id:      Optional[str]   = None,
        version:        str             = "1.0.0",
    ) -> MarketPolicy:
        """Create a policy with no rules that always returns *default_action*."""
        return MarketPolicy.create(
            name           = name,
            policy_type    = policy_type,
            priority       = priority,
            rules          = [],
            version        = version,
            policy_id      = policy_id,
            default_action = default_action,
            enabled        = enabled,
            description    = description,
        )

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def create_policy_result(
        self,
        policy_id:   str,
        policy_name: str,
        policy_type: MarketPolicyType,
        priority:    PolicyPriority,
        action:      PolicyAction,
        *,
        rationale:            str                      = "",
        triggered_rule_id:    str                      = "",
        triggered_rule_name:  str                      = "",
        conditions_met:       Tuple[str, ...]          = (),
        conditions_failed:    Tuple[str, ...]          = (),
        evaluation_elapsed_s: float                    = 0.0,
        metadata:             Optional[Dict[str, Any]] = None,
    ) -> MarketPolicyResult:
        return MarketPolicyResult.create(
            policy_id            = policy_id,
            policy_name          = policy_name,
            policy_type          = policy_type,
            priority             = priority,
            action               = action,
            rationale            = rationale,
            triggered_rule_id    = triggered_rule_id,
            triggered_rule_name  = triggered_rule_name,
            conditions_met       = conditions_met,
            conditions_failed    = conditions_failed,
            evaluation_elapsed_s = evaluation_elapsed_s,
            metadata             = metadata,
        )
