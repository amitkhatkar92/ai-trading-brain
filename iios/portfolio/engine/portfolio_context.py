"""
portfolio_context.py — iios.portfolio.engine
=============================================
Immutable engine-level context attached to a portfolio workflow request.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    PortfolioWorkflowType,
    SchedulerPriority,
)


@dataclass(frozen=True)
class PortfolioContext:
    """
    Immutable engine-level context for a portfolio workflow request.

    Carries the operational parameters that parameterise how the engine
    processes a single portfolio workflow.

    Fields
    ------
    context_id :        Unique identifier.
    portfolio_id :      Target portfolio identifier.
    workflow_type :     Requested workflow classification.
    priority :          Scheduling priority.
    source :            Requesting component or actor identifier.
    correlation_id :    Upstream correlation identifier (e.g. decision_id).
    metadata :          Supplementary context metadata.
    framework_version : Framework version string.
    """
    context_id:        str
    portfolio_id:      str
    workflow_type:     PortfolioWorkflowType  = PortfolioWorkflowType.PORTFOLIO_CREATION
    priority:          SchedulerPriority       = SchedulerPriority.NORMAL
    source:            str                    = ""
    correlation_id:    str                    = ""
    metadata:          Dict[str, Any]         = field(default_factory=dict)
    framework_version: str                    = VERSION

    @classmethod
    def create(
        cls,
        portfolio_id: str,
        *,
        context_id:     Optional[str]               = None,
        workflow_type:  PortfolioWorkflowType         = PortfolioWorkflowType.PORTFOLIO_CREATION,
        priority:       SchedulerPriority             = SchedulerPriority.NORMAL,
        source:         str                          = "",
        correlation_id: str                          = "",
        metadata:       Optional[Dict[str, Any]]     = None,
    ) -> "PortfolioContext":
        return cls(
            context_id      = context_id or str(uuid.uuid4()),
            portfolio_id    = portfolio_id,
            workflow_type   = workflow_type,
            priority        = priority,
            source          = source,
            correlation_id  = correlation_id,
            metadata        = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":        self.context_id,
            "portfolio_id":      self.portfolio_id,
            "workflow_type":     self.workflow_type.value,
            "priority":          self.priority.value,
            "source":            self.source,
            "correlation_id":    self.correlation_id,
            "framework_version": self.framework_version,
        }
