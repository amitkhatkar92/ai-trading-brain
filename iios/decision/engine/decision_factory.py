"""
decision_factory.py — iios.decision.engine
============================================
Stateless factory for creating decision engine objects.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from .constants import (
    DecisionMode,
    DecisionPriority,
    DEFAULT_DEADLINE_S,
)
from .decision_request  import DecisionRequest
from .decision_pipeline import DecisionPipeline


class DecisionEngineFactory:
    """
    Stateless factory for :class:`DecisionRequest` and
    :class:`DecisionPipeline` objects.

    All factory methods are pure functions — no side effects.
    """

    # ------------------------------------------------------------------
    # Request factory
    # ------------------------------------------------------------------
    def create_request(
        self,
        decision_id: str,
        *,
        request_id:      Optional[str]         = None,
        workflow_id:     str                   = "",
        portfolio_id:    str                   = "",
        strategy_id:     str                   = "",
        decision_mode:   DecisionMode          = DecisionMode.REAL_TIME,
        decision_reason: str                   = "",
        priority:        DecisionPriority      = DecisionPriority.MEDIUM,
        deadline_s:      float                 = DEFAULT_DEADLINE_S,
        inputs:          Optional[Dict[str, Any]] = None,
        metadata:        Optional[Dict[str, Any]] = None,
    ) -> DecisionRequest:
        """Create a :class:`DecisionRequest`."""
        return DecisionRequest.create(
            decision_id,
            request_id      = request_id,
            workflow_id     = workflow_id,
            portfolio_id    = portfolio_id,
            strategy_id     = strategy_id,
            decision_mode   = decision_mode,
            decision_reason = decision_reason,
            priority        = priority,
            deadline_s      = deadline_s,
            inputs          = inputs,
            metadata        = metadata,
        )

    # ------------------------------------------------------------------
    # Pipeline factory
    # ------------------------------------------------------------------
    def create_pipeline(
        self,
        *,
        pipeline_id:  Optional[str] = None,
        session_id:   str           = "",
        request_id:   str           = "",
        decision_id:  str           = "",
        workflow_id:  str           = "",
        portfolio_id: str           = "",
        strategy_id:  str           = "",
    ) -> DecisionPipeline:
        """Create a :class:`DecisionPipeline`."""
        return DecisionPipeline(
            pipeline_id  = pipeline_id,
            session_id   = session_id,
            request_id   = request_id,
            decision_id  = decision_id,
            workflow_id  = workflow_id,
            portfolio_id = portfolio_id,
            strategy_id  = strategy_id,
        )
