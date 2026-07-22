"""
risk_policy_factory.py — iios.risk.policies
=============================================
Factory for creating Risk Policy Framework objects with sensible defaults.

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    DEFAULT_POLICY_ACTION,
    VERSION,
    EvaluationMode,
    PolicyAction,
    PolicyPriority,
    PolicyType,
)
from .risk_policy import RiskPolicy
from .risk_policy_audit import RiskPolicyAuditReport
from .risk_policy_context import RiskPolicyContext
from .risk_policy_request import RiskPolicyRequest
from .risk_policy_response import RiskEvaluationSummary, RiskPolicyResponse
from .risk_policy_result import RiskPolicyResult
from .risk_policy_rule import RiskPolicyRule


class RiskPolicyFactory:
    """
    Convenience factory for constructing Risk Policy Framework objects.

    All methods return fully-initialised immutable value objects with
    sensible defaults.  The factory performs no evaluation logic.
    """

    # ------------------------------------------------------------------
    # Context & Request
    # ------------------------------------------------------------------

    def create_context(
        self,
        evaluation_id: str,
        portfolio_id:  str,
        risk_id:       str,
        *,
        source:         str                               = "",
        policy_types:   Optional[Tuple[PolicyType, ...]] = None,
        priority_floor: PolicyPriority                    = PolicyPriority.INFORMATIONAL,
        correlation_id: str                               = "",
        metadata:       Optional[Dict[str, Any]]          = None,
    ) -> RiskPolicyContext:
        return RiskPolicyContext.create(
            evaluation_id  = evaluation_id,
            portfolio_id   = portfolio_id,
            risk_id        = risk_id,
            source         = source,
            policy_types   = policy_types,
            priority_floor = priority_floor,
            correlation_id = correlation_id,
            metadata       = metadata,
        )

    def create_request(
        self,
        evaluation_id: str,
        portfolio_id:  str,
        risk_id:       str,
        *,
        inputs:      Optional[Dict[str, Any]]    = None,
        context:     Optional[RiskPolicyContext] = None,
        request_id:  Optional[str]               = None,
        metadata:    Optional[Dict[str, Any]]    = None,
    ) -> RiskPolicyRequest:
        return RiskPolicyRequest.create(
            evaluation_id = evaluation_id,
            portfolio_id  = portfolio_id,
            risk_id       = risk_id,
            request_id    = request_id,
            context       = context,
            inputs        = inputs,
            metadata      = metadata,
        )

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------

    def create_simple_policy(
        self,
        name:        str,
        policy_type: PolicyType,
        priority:    PolicyPriority    = PolicyPriority.MEDIUM,
        *,
        default_action:  PolicyAction    = DEFAULT_POLICY_ACTION,
        enabled:         bool            = True,
        description:     str             = "",
        policy_id:       Optional[str]   = None,
        version:         str             = "1.0.0",
    ) -> RiskPolicy:
        """Create a policy with no rules that always returns *default_action*."""
        return RiskPolicy.create(
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
        policy_type: PolicyType,
        priority:    PolicyPriority,
        action:      PolicyAction,
        *,
        triggered_rule_id:   str             = "",
        triggered_rule_name: str             = "",
        rationale:           str             = "",
        elapsed_s:           float           = 0.0,
    ) -> RiskPolicyResult:
        return RiskPolicyResult.create(
            policy_id             = policy_id,
            policy_name           = policy_name,
            policy_type           = policy_type,
            priority              = priority,
            action                = action,
            triggered_rule_id     = triggered_rule_id,
            triggered_rule_name   = triggered_rule_name,
            rationale             = rationale,
            evaluation_elapsed_s  = elapsed_s,
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def create_evaluation_summary(
        self,
        results:      List[RiskPolicyResult],
        final_action: PolicyAction,
        *,
        dominant_policy_id:   str = "",
        dominant_policy_name: str = "",
        rationale:            str = "",
    ) -> RiskEvaluationSummary:
        return RiskEvaluationSummary.from_results(
            tuple(results),
            final_action,
            dominant_policy_id   = dominant_policy_id,
            dominant_policy_name = dominant_policy_name,
            rationale            = rationale,
        )

    # ------------------------------------------------------------------
    # Response
    # ------------------------------------------------------------------

    def create_response(
        self,
        request:      RiskPolicyRequest,
        final_action: PolicyAction,
        results:      List[RiskPolicyResult],
        summary:      RiskEvaluationSummary,
        elapsed_s:    float,
        *,
        response_id: Optional[str]            = None,
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> RiskPolicyResponse:
        return RiskPolicyResponse.create_success(
            request_id           = request.request_id,
            evaluation_id        = request.evaluation_id,
            portfolio_id         = request.portfolio_id,
            risk_id              = request.risk_id,
            final_action         = final_action,
            results              = tuple(results),
            summary              = summary,
            evaluation_elapsed_s = elapsed_s,
            response_id          = response_id,
            metadata             = metadata,
        )
