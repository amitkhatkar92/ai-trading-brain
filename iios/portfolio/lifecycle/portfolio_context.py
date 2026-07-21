"""
portfolio_context.py — iios.portfolio.lifecycle
=================================================
Immutable operational context attached to a portfolio session.

C10 Portfolio Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    PortfolioObjective,
    PortfolioScope,
    PortfolioType,
)


@dataclass(frozen=True)
class PortfolioContext:
    """
    Immutable operational context that parameterises a portfolio session.

    Captured at session creation; never mutated afterwards.

    Fields
    ------
    context_id :       Unique identifier.
    portfolio_id :     Caller-supplied portfolio identifier.
    portfolio_name :   Human-readable portfolio name.
    portfolio_type :   Asset-composition classification.
    portfolio_scope :  Institutional scope.
    portfolio_objective: Investment objective.
    portfolio_currency : Base currency (ISO 4217, e.g. "INR", "USD").
    workflow_id :      Optional workflow routing context.
    metadata :         Supplementary context metadata.
    framework_version: Framework version.
    """
    context_id:           str
    portfolio_id:         str
    portfolio_name:       str                = ""
    portfolio_type:       PortfolioType      = PortfolioType.CUSTOM
    portfolio_scope:      PortfolioScope     = PortfolioScope.INSTITUTIONAL
    portfolio_objective:  PortfolioObjective = PortfolioObjective.CUSTOM
    portfolio_currency:   str                = "INR"
    workflow_id:          str                = ""
    metadata:             Dict[str, Any]     = field(default_factory=dict)
    framework_version:    str                = VERSION

    @classmethod
    def create(
        cls,
        portfolio_id: str,
        *,
        context_id:          Optional[str]          = None,
        portfolio_name:      str                    = "",
        portfolio_type:      PortfolioType           = PortfolioType.CUSTOM,
        portfolio_scope:     PortfolioScope          = PortfolioScope.INSTITUTIONAL,
        portfolio_objective: PortfolioObjective      = PortfolioObjective.CUSTOM,
        portfolio_currency:  str                    = "INR",
        workflow_id:         str                    = "",
        metadata:            Optional[Dict[str, Any]] = None,
    ) -> "PortfolioContext":
        return cls(
            context_id           = context_id or str(uuid.uuid4()),
            portfolio_id         = portfolio_id,
            portfolio_name       = portfolio_name,
            portfolio_type       = portfolio_type,
            portfolio_scope      = portfolio_scope,
            portfolio_objective  = portfolio_objective,
            portfolio_currency   = portfolio_currency,
            workflow_id          = workflow_id,
            metadata             = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":           self.context_id,
            "portfolio_id":         self.portfolio_id,
            "portfolio_name":       self.portfolio_name,
            "portfolio_type":       self.portfolio_type.value,
            "portfolio_scope":      self.portfolio_scope.value,
            "portfolio_objective":  self.portfolio_objective.value,
            "portfolio_currency":   self.portfolio_currency,
            "workflow_id":          self.workflow_id,
            "framework_version":    self.framework_version,
        }
