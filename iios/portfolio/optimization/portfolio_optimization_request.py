"""
portfolio_optimization_request.py — iios.portfolio.optimization
================================================================
Immutable optimization request carrying candidates and inputs.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .constants import VERSION, DEFAULT_STRATEGY_NAME
from .portfolio_candidate import PortfolioCandidate
from .portfolio_optimization_context import OptimizationContext


@dataclass(frozen=True)
class PortfolioOptimizationRequest:
    """
    Immutable request submitted to the optimization engine.

    Fields
    ------
    request_id :      Unique identifier.
    portfolio_id :    Portfolio being optimized.
    optimization_id : Pre-assigned run identifier (matches context).
    strategy_name :   Name of the optimization strategy to apply.
    candidates :      Tuple of approved portfolio candidates.
    inputs :          Input snapshots (market data, positions, etc.).
    context :         Immutable run context.
    requested_at :    Wall-clock submission timestamp.
    metadata :        Supplementary data.
    framework_version : Framework version string.
    """
    request_id:        str
    portfolio_id:      str
    optimization_id:   str
    strategy_name:     str
    candidates:        tuple   # Tuple[PortfolioCandidate, ...]
    inputs:            Dict[str, Any]
    context:           OptimizationContext
    requested_at:      float
    metadata:          Dict[str, Any]
    framework_version: str

    @classmethod
    def create(
        cls,
        portfolio_id:    str,
        *,
        strategy_name:   str = DEFAULT_STRATEGY_NAME,
        candidates:      Optional[List[PortfolioCandidate]] = None,
        inputs:          Optional[Dict[str, Any]] = None,
        context:         Optional[OptimizationContext] = None,
        optimization_id: str = "",
        metadata:        Optional[Dict[str, Any]] = None,
    ) -> "PortfolioOptimizationRequest":
        oid = optimization_id or str(uuid.uuid4())
        ctx = context or OptimizationContext.create(
            portfolio_id,
            strategy_name   = strategy_name,
            optimization_id = oid,
        )
        return cls(
            request_id        = str(uuid.uuid4()),
            portfolio_id      = portfolio_id,
            optimization_id   = oid,
            strategy_name     = strategy_name,
            candidates        = tuple(candidates or []),
            inputs            = dict(inputs or {}),
            context           = ctx,
            requested_at      = time.time(),
            metadata          = dict(metadata or {}),
            framework_version = VERSION,
        )

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    def with_candidates(
        self, candidates: List[PortfolioCandidate]
    ) -> "PortfolioOptimizationRequest":
        """Return a new request with the given candidates."""
        return PortfolioOptimizationRequest(
            request_id        = self.request_id,
            portfolio_id      = self.portfolio_id,
            optimization_id   = self.optimization_id,
            strategy_name     = self.strategy_name,
            candidates        = tuple(candidates),
            inputs            = self.inputs,
            context           = self.context,
            requested_at      = self.requested_at,
            metadata          = self.metadata,
            framework_version = self.framework_version,
        )

    def with_inputs(self, inputs: Dict[str, Any]) -> "PortfolioOptimizationRequest":
        """Return a new request with the given inputs."""
        return PortfolioOptimizationRequest(
            request_id        = self.request_id,
            portfolio_id      = self.portfolio_id,
            optimization_id   = self.optimization_id,
            strategy_name     = self.strategy_name,
            candidates        = self.candidates,
            inputs            = dict(inputs),
            context           = self.context,
            requested_at      = self.requested_at,
            metadata          = self.metadata,
            framework_version = self.framework_version,
        )

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":        self.request_id,
            "portfolio_id":      self.portfolio_id,
            "optimization_id":   self.optimization_id,
            "strategy_name":     self.strategy_name,
            "candidate_count":   self.candidate_count,
            "input_keys":        sorted(self.inputs.keys()),
            "requested_at":      self.requested_at,
            "framework_version": self.framework_version,
        }
