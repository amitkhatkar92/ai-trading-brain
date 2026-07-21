"""
portfolio_request.py — iios.portfolio.engine
=============================================
Immutable portfolio workflow request value object.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    PortfolioWorkflowType,
    SchedulerPriority,
)
from .portfolio_context import PortfolioContext


@dataclass(frozen=True)
class PortfolioRequest:
    """
    Immutable portfolio workflow request.

    Wraps all inputs required to execute a single portfolio workflow pipeline.

    Fields
    ------
    request_id :        Unique request identifier.
    portfolio_id :      Target portfolio identifier.
    workflow_type :     Workflow classification.
    priority :          Scheduling priority.
    context :           Engine-level operational context.
    inputs :            Dict of collected institutional snapshots.
                        Keys: "decision_snapshot", "order_snapshot",
                        "position_snapshot", "account_snapshot", etc.
    requested_at :      Wall-clock request creation time.
    metadata :          Supplementary request metadata.
    framework_version : Framework version string.
    """
    request_id:        str
    portfolio_id:      str
    workflow_type:     PortfolioWorkflowType
    priority:          SchedulerPriority
    context:           PortfolioContext
    inputs:            Dict[str, Any]     = field(default_factory=dict)
    requested_at:      float              = field(default_factory=time.time)
    metadata:          Dict[str, Any]     = field(default_factory=dict)
    framework_version: str               = VERSION

    @classmethod
    def create(
        cls,
        portfolio_id:  str,
        workflow_type: PortfolioWorkflowType = PortfolioWorkflowType.PORTFOLIO_CREATION,
        *,
        request_id:    Optional[str]             = None,
        priority:      SchedulerPriority          = SchedulerPriority.NORMAL,
        context:       Optional[PortfolioContext] = None,
        inputs:        Optional[Dict[str, Any]]   = None,
        metadata:      Optional[Dict[str, Any]]   = None,
    ) -> "PortfolioRequest":
        rid = request_id or str(uuid.uuid4())
        ctx = context or PortfolioContext.create(
            portfolio_id,
            workflow_type = workflow_type,
            priority      = priority,
        )
        return cls(
            request_id    = rid,
            portfolio_id  = portfolio_id,
            workflow_type = workflow_type,
            priority      = priority,
            context       = ctx,
            inputs        = dict(inputs or {}),
            metadata      = dict(metadata or {}),
        )

    def with_inputs(self, inputs: Dict[str, Any]) -> "PortfolioRequest":
        """Return a new request with the given inputs merged in."""
        merged = {**self.inputs, **inputs}
        return PortfolioRequest(
            request_id        = self.request_id,
            portfolio_id      = self.portfolio_id,
            workflow_type     = self.workflow_type,
            priority          = self.priority,
            context           = self.context,
            inputs            = merged,
            requested_at      = self.requested_at,
            metadata          = dict(self.metadata),
            framework_version = self.framework_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":        self.request_id,
            "portfolio_id":      self.portfolio_id,
            "workflow_type":     self.workflow_type.value,
            "priority":          self.priority.value,
            "input_keys":        list(self.inputs.keys()),
            "requested_at":      self.requested_at,
            "framework_version": self.framework_version,
        }
