"""
portfolio_optimization_events.py — iios.portfolio.optimization
===============================================================
OptimizationEngineEvent and 10 factory functions.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .constants import (
    ACTOR_ENGINE,
    ACTOR_OPTIMIZER,
    ACTOR_SELECTOR,
    OPTIMIZATION_SYSTEM_ID,
    OptimizationEventType,
    VERSION,
)


@dataclass(frozen=True)
class OptimizationEngineEvent:
    """
    Immutable event produced by the optimization engine.
    """
    event_id:          str
    event_type:        OptimizationEventType
    optimization_id:   str
    portfolio_id:      str
    actor:             str
    payload:           Dict[str, Any]
    occurred_at:       float
    framework_version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":         self.event_id,
            "event_type":       self.event_type.value,
            "optimization_id":  self.optimization_id,
            "portfolio_id":     self.portfolio_id,
            "actor":            self.actor,
            "payload":          dict(self.payload),
            "occurred_at":      self.occurred_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def _make(
    event_type:      OptimizationEventType,
    optimization_id: str,
    portfolio_id:    str,
    actor:           str,
    payload:         Dict[str, Any],
) -> OptimizationEngineEvent:
    return OptimizationEngineEvent(
        event_id          = str(uuid.uuid4()),
        event_type        = event_type,
        optimization_id   = optimization_id,
        portfolio_id      = portfolio_id,
        actor             = actor,
        payload           = payload,
        occurred_at       = time.time(),
        framework_version = VERSION,
    )


def make_optimization_started(
    optimization_id: str,
    portfolio_id:    str,
    candidate_count: int = 0,
) -> OptimizationEngineEvent:
    return _make(
        OptimizationEventType.OPTIMIZATION_STARTED,
        optimization_id, portfolio_id, ACTOR_ENGINE,
        {"candidate_count": candidate_count},
    )


def make_candidates_loaded(
    optimization_id: str,
    portfolio_id:    str,
    count:           int = 0,
) -> OptimizationEngineEvent:
    return _make(
        OptimizationEventType.CANDIDATES_LOADED,
        optimization_id, portfolio_id, ACTOR_OPTIMIZER,
        {"count": count},
    )


def make_objectives_loaded(
    optimization_id: str,
    portfolio_id:    str,
    count:           int = 0,
) -> OptimizationEngineEvent:
    return _make(
        OptimizationEventType.OBJECTIVES_LOADED,
        optimization_id, portfolio_id, ACTOR_OPTIMIZER,
        {"count": count},
    )


def make_constraints_loaded(
    optimization_id: str,
    portfolio_id:    str,
    count:           int = 0,
) -> OptimizationEngineEvent:
    return _make(
        OptimizationEventType.CONSTRAINTS_LOADED,
        optimization_id, portfolio_id, ACTOR_OPTIMIZER,
        {"count": count},
    )


def make_allocation_generated(
    optimization_id: str,
    portfolio_id:    str,
    candidate_id:    str = "",
) -> OptimizationEngineEvent:
    return _make(
        OptimizationEventType.ALLOCATION_GENERATED,
        optimization_id, portfolio_id, ACTOR_OPTIMIZER,
        {"candidate_id": candidate_id},
    )


def make_rebalancing_generated(
    optimization_id: str,
    portfolio_id:    str,
    candidate_id:    str = "",
) -> OptimizationEngineEvent:
    return _make(
        OptimizationEventType.REBALANCING_GENERATED,
        optimization_id, portfolio_id, ACTOR_OPTIMIZER,
        {"candidate_id": candidate_id},
    )


def make_optimization_completed(
    optimization_id: str,
    portfolio_id:    str,
    elapsed_s:       float = 0.0,
    candidate_id:    str   = "",
) -> OptimizationEngineEvent:
    return _make(
        OptimizationEventType.OPTIMIZATION_COMPLETED,
        optimization_id, portfolio_id, ACTOR_ENGINE,
        {"elapsed_s": elapsed_s, "selected_candidate_id": candidate_id},
    )


def make_portfolio_selected(
    optimization_id: str,
    portfolio_id:    str,
    candidate_id:    str   = "",
    score:           float = 0.0,
) -> OptimizationEngineEvent:
    return _make(
        OptimizationEventType.PORTFOLIO_SELECTED,
        optimization_id, portfolio_id, ACTOR_SELECTOR,
        {"candidate_id": candidate_id, "score": score},
    )


def make_solution_validated(
    optimization_id: str,
    portfolio_id:    str,
    is_valid:        bool = True,
) -> OptimizationEngineEvent:
    return _make(
        OptimizationEventType.SOLUTION_VALIDATED,
        optimization_id, portfolio_id, ACTOR_SELECTOR,
        {"is_valid": is_valid},
    )


def make_optimization_failed(
    optimization_id: str,
    portfolio_id:    str,
    reason:          str = "",
) -> OptimizationEngineEvent:
    return _make(
        OptimizationEventType.OPTIMIZATION_FAILED,
        optimization_id, portfolio_id, ACTOR_ENGINE,
        {"reason": reason},
    )
