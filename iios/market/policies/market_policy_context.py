"""
market_policy_context.py — iios.market.policies
=================================================
Immutable engine-level context for a market policy evaluation run.

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION, MarketPolicyType, PolicyPriority


@dataclass(frozen=True)
class MarketPolicyContext:
    """
    Immutable operational context attached to a market policy evaluation request.

    Carries the governance parameters that shape how the market policy engine
    processes a single evaluation.

    Fields
    ------
    context_id :          Unique identifier.
    evaluation_id :       Correlation identifier linking to the originating
                          market intelligence workflow.
    market_analysis_id :  Target market analysis identifier.
    exchange :            Exchange identifier (e.g. ``"NSE"``, ``"BSE"``).
    policy_types :        Policy domains to include in evaluation (empty = all).
    priority_floor :      Minimum priority level to consider (inclusive).
    source :              Requesting component or actor identifier.
    correlation_id :      Upstream correlation identifier.
    metadata :            Supplementary context metadata.
    framework_version :   Framework version string.
    """
    context_id:          str
    evaluation_id:       str
    market_analysis_id:  str
    exchange:            str
    policy_types:        Tuple[MarketPolicyType, ...] = field(default_factory=tuple)
    priority_floor:      PolicyPriority               = PolicyPriority.INFORMATIONAL
    source:              str                          = ""
    correlation_id:      str                          = ""
    metadata:            Dict[str, Any]               = field(default_factory=dict)
    framework_version:   str                          = VERSION

    @classmethod
    def create(
        cls,
        evaluation_id:      str,
        market_analysis_id: str,
        exchange:           str,
        *,
        context_id:     Optional[str]                          = None,
        policy_types:   Optional[Tuple[MarketPolicyType, ...]] = None,
        priority_floor: PolicyPriority                         = PolicyPriority.INFORMATIONAL,
        source:         str                                    = "",
        correlation_id: str                                    = "",
        metadata:       Optional[Dict[str, Any]]               = None,
    ) -> "MarketPolicyContext":
        return cls(
            context_id          = context_id or str(uuid.uuid4()),
            evaluation_id       = evaluation_id,
            market_analysis_id  = market_analysis_id,
            exchange            = exchange,
            policy_types        = tuple(policy_types or []),
            priority_floor      = priority_floor,
            source              = source,
            correlation_id      = correlation_id,
            metadata            = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":          self.context_id,
            "evaluation_id":       self.evaluation_id,
            "market_analysis_id":  self.market_analysis_id,
            "exchange":            self.exchange,
            "policy_types":        [pt.value for pt in self.policy_types],
            "priority_floor":      self.priority_floor.value,
            "source":              self.source,
            "correlation_id":      self.correlation_id,
            "framework_version":   self.framework_version,
        }
