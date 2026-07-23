"""
market_policy_request.py — iios.market.policies
=================================================
Immutable market policy evaluation request value object.

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION
from .market_policy_context import MarketPolicyContext


@dataclass(frozen=True)
class MarketPolicyRequest:
    """
    Immutable request submitted to the Market Policy Framework for evaluation.

    The ``inputs`` dict carries all observable market factors that policies
    will evaluate against.  No quantitative calculations are performed here;
    the dict is treated as a plain key-value lookup store.

    Fields
    ------
    request_id :          Unique identifier.
    evaluation_id :       Links this request to an originating market workflow.
    market_analysis_id :  Target market analysis identifier.
    exchange :            Exchange identifier (e.g. ``"NSE"``, ``"BSE"``).
    context :             Operational evaluation context.
    inputs :              Flat dict of observable market factors.
    requested_at :        Wall-clock submission time.
    metadata :            Supplementary metadata.
    framework_version :   Framework version string.
    """
    request_id:          str
    evaluation_id:       str
    market_analysis_id:  str
    exchange:            str
    context:             MarketPolicyContext
    inputs:              Dict[str, Any]   = field(default_factory=dict)
    requested_at:        float            = field(default_factory=time.time)
    metadata:            Dict[str, Any]   = field(default_factory=dict)
    framework_version:   str              = VERSION

    @classmethod
    def create(
        cls,
        evaluation_id:      str,
        market_analysis_id: str,
        exchange:           str,
        *,
        request_id: Optional[str]               = None,
        context:    Optional[MarketPolicyContext] = None,
        inputs:     Optional[Dict[str, Any]]     = None,
        metadata:   Optional[Dict[str, Any]]     = None,
    ) -> "MarketPolicyRequest":
        ctx = context or MarketPolicyContext.create(
            evaluation_id      = evaluation_id,
            market_analysis_id = market_analysis_id,
            exchange           = exchange,
        )
        return cls(
            request_id         = request_id or str(uuid.uuid4()),
            evaluation_id      = evaluation_id,
            market_analysis_id = market_analysis_id,
            exchange           = exchange,
            context            = ctx,
            inputs             = dict(inputs or {}),
            metadata           = dict(metadata or {}),
        )

    def with_inputs(self, inputs: Dict[str, Any]) -> "MarketPolicyRequest":
        """Return a new request with additional or replaced inputs."""
        merged = {**self.inputs, **inputs}
        return MarketPolicyRequest(
            request_id         = self.request_id,
            evaluation_id      = self.evaluation_id,
            market_analysis_id = self.market_analysis_id,
            exchange           = self.exchange,
            context            = self.context,
            inputs             = merged,
            requested_at       = self.requested_at,
            metadata           = self.metadata,
            framework_version  = self.framework_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":          self.request_id,
            "evaluation_id":       self.evaluation_id,
            "market_analysis_id":  self.market_analysis_id,
            "exchange":            self.exchange,
            "context":             self.context.to_dict(),
            "input_keys":          list(self.inputs.keys()),
            "requested_at":        self.requested_at,
            "framework_version":   self.framework_version,
        }
