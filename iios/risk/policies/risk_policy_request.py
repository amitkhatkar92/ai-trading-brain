"""
risk_policy_request.py — iios.risk.policies
=============================================
Immutable policy evaluation request value object.

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION
from .risk_policy_context import RiskPolicyContext


@dataclass(frozen=True)
class RiskPolicyRequest:
    """
    Immutable request submitted to the Risk Policy Framework for evaluation.

    The ``inputs`` dict carries all observable risk factors that policies
    will evaluate against.  No quantitative calculations are performed here;
    the dict is treated as a plain key-value lookup store.

    Fields
    ------
    request_id :        Unique identifier.
    evaluation_id :     Links this request to an originating risk workflow.
    portfolio_id :      Target portfolio identifier.
    risk_id :           Originating risk assessment identifier.
    context :           Operational evaluation context.
    inputs :            Flat dict of observable risk factors.
    requested_at :      Wall-clock submission time.
    metadata :          Supplementary metadata.
    framework_version : Framework version string.
    """
    request_id:        str
    evaluation_id:     str
    portfolio_id:      str
    risk_id:           str
    context:           RiskPolicyContext
    inputs:            Dict[str, Any]   = field(default_factory=dict)
    requested_at:      float            = field(default_factory=time.time)
    metadata:          Dict[str, Any]   = field(default_factory=dict)
    framework_version: str              = VERSION

    @classmethod
    def create(
        cls,
        evaluation_id: str,
        portfolio_id:  str,
        risk_id:       str,
        *,
        request_id:  Optional[str]            = None,
        context:     Optional[RiskPolicyContext] = None,
        inputs:      Optional[Dict[str, Any]]  = None,
        metadata:    Optional[Dict[str, Any]]  = None,
    ) -> "RiskPolicyRequest":
        ctx = context or RiskPolicyContext.create(
            evaluation_id = evaluation_id,
            portfolio_id  = portfolio_id,
            risk_id       = risk_id,
        )
        return cls(
            request_id    = request_id or str(uuid.uuid4()),
            evaluation_id = evaluation_id,
            portfolio_id  = portfolio_id,
            risk_id       = risk_id,
            context       = ctx,
            inputs        = dict(inputs or {}),
            metadata      = dict(metadata or {}),
        )

    def with_inputs(self, inputs: Dict[str, Any]) -> "RiskPolicyRequest":
        """Return a new request with additional or replaced inputs."""
        merged = {**self.inputs, **inputs}
        return RiskPolicyRequest(
            request_id    = self.request_id,
            evaluation_id = self.evaluation_id,
            portfolio_id  = self.portfolio_id,
            risk_id       = self.risk_id,
            context       = self.context,
            inputs        = merged,
            requested_at  = self.requested_at,
            metadata      = self.metadata,
            framework_version = self.framework_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":        self.request_id,
            "evaluation_id":     self.evaluation_id,
            "portfolio_id":      self.portfolio_id,
            "risk_id":           self.risk_id,
            "context":           self.context.to_dict(),
            "input_keys":        list(self.inputs.keys()),
            "requested_at":      self.requested_at,
            "framework_version": self.framework_version,
        }
