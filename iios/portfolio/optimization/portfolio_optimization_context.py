"""
portfolio_optimization_context.py — iios.portfolio.optimization
================================================================
Immutable evaluation context for one optimization run.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .constants import (
    OPTIMIZATION_SYSTEM_ID,
    VERSION,
    OptimizationObjective,
    OptimizationStrategyType,
)


@dataclass(frozen=True)
class OptimizationContext:
    """
    Immutable context attached to every portfolio optimization run.

    Fields
    ------
    context_id :        Unique identifier.
    portfolio_id :      Portfolio being optimized.
    strategy_name :     Name of the optimization strategy to apply.
    objectives :        Tuple of objective types to optimize for.
    source :            Identifier of the originating component.
    correlation_id :    Optional trace correlation identifier.
    optimization_id :   Pre-assigned optimization run identifier.
    metadata :          Supplementary free-form data.
    framework_version : Framework version string.
    """
    context_id:        str
    portfolio_id:      str
    strategy_name:     str
    objectives:        tuple   # Tuple[OptimizationObjective, ...]
    source:            str
    correlation_id:    str
    optimization_id:   str
    metadata:          Dict[str, Any]
    framework_version: str

    @classmethod
    def create(
        cls,
        portfolio_id:    str,
        *,
        strategy_name:   str = "default",
        objectives:      Optional[List[OptimizationObjective]] = None,
        source:          str = OPTIMIZATION_SYSTEM_ID,
        correlation_id:  str = "",
        optimization_id: str = "",
        metadata:        Optional[Dict[str, Any]] = None,
    ) -> "OptimizationContext":
        return cls(
            context_id        = str(uuid.uuid4()),
            portfolio_id      = portfolio_id,
            strategy_name     = strategy_name,
            objectives        = tuple(objectives or []),
            source            = source,
            correlation_id    = correlation_id,
            optimization_id   = optimization_id or str(uuid.uuid4()),
            metadata          = dict(metadata or {}),
            framework_version = VERSION,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":       self.context_id,
            "portfolio_id":     self.portfolio_id,
            "strategy_name":    self.strategy_name,
            "objectives":       [o.value for o in self.objectives],
            "source":           self.source,
            "correlation_id":   self.correlation_id,
            "optimization_id":  self.optimization_id,
            "framework_version": self.framework_version,
        }
