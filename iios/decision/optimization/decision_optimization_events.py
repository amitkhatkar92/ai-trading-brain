"""
decision_optimization_events.py — iios.decision.optimization
=============================================================
Event value objects and factory functions for the Optimization Framework.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import VERSION, OptimizationEventType


@dataclass(frozen=True)
class DecisionOptimizationEvent:
    """
    Immutable event emitted during an optimization run.

    Parameters
    ----------
    event_id :          Unique event identifier.
    event_type :        Kind of event.
    request_id :        Originating request ID.
    decision_id :       Decision being optimized.
    source :            Component that emitted the event.
    payload :           Event-specific data.
    occurred_at :       Timestamp.
    framework_version : Version string.
    """

    event_id:          str
    event_type:        OptimizationEventType
    request_id:        str
    decision_id:       str
    source:            str
    payload:           Dict[str, Any]
    occurred_at:       datetime
    framework_version: str = VERSION

    def to_dict(self) -> dict:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "request_id":        self.request_id,
            "decision_id":       self.decision_id,
            "source":            self.source,
            "payload":           self.payload,
            "occurred_at":       self.occurred_at.isoformat(),
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _make_event(
    event_type:  OptimizationEventType,
    request_id:  str,
    decision_id: str,
    source:      str,
    payload:     Dict[str, Any],
) -> DecisionOptimizationEvent:
    return DecisionOptimizationEvent(
        event_id    = str(uuid.uuid4()),
        event_type  = event_type,
        request_id  = request_id,
        decision_id = decision_id,
        source      = source,
        payload     = payload,
        occurred_at = datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Factory functions — one per OptimizationEventType
# ---------------------------------------------------------------------------

def make_optimization_started(
    request_id:       str,
    decision_id:      str,
    source:           str,
    *,
    candidate_count:  int = 0,
    strategy:         str = "",
) -> DecisionOptimizationEvent:
    return _make_event(
        OptimizationEventType.OPTIMIZATION_STARTED,
        request_id, decision_id, source,
        {"candidate_count": candidate_count, "strategy": strategy},
    )


def make_candidates_loaded(
    request_id:      str,
    decision_id:     str,
    source:          str,
    *,
    count:           int = 0,
) -> DecisionOptimizationEvent:
    return _make_event(
        OptimizationEventType.CANDIDATES_LOADED,
        request_id, decision_id, source,
        {"count": count},
    )


def make_objectives_loaded(
    request_id:      str,
    decision_id:     str,
    source:          str,
    *,
    count:           int = 0,
) -> DecisionOptimizationEvent:
    return _make_event(
        OptimizationEventType.OBJECTIVES_LOADED,
        request_id, decision_id, source,
        {"count": count},
    )


def make_constraints_loaded(
    request_id:      str,
    decision_id:     str,
    source:          str,
    *,
    count:           int = 0,
) -> DecisionOptimizationEvent:
    return _make_event(
        OptimizationEventType.CONSTRAINTS_LOADED,
        request_id, decision_id, source,
        {"count": count},
    )


def make_optimization_completed(
    request_id:        str,
    decision_id:       str,
    source:            str,
    *,
    selected_id:       str   = "",
    final_score:       float = 0.0,
    evaluation_time_s: float = 0.0,
    is_optimal:        bool  = False,
) -> DecisionOptimizationEvent:
    return _make_event(
        OptimizationEventType.OPTIMIZATION_COMPLETED,
        request_id, decision_id, source,
        {
            "selected_candidate_id": selected_id,
            "final_score":           final_score,
            "evaluation_time_s":     evaluation_time_s,
            "is_optimal":            is_optimal,
        },
    )


def make_solution_selected(
    request_id:      str,
    decision_id:     str,
    source:          str,
    *,
    solution_id:     str  = "",
    rank:            int  = 1,
    is_optimal:      bool = False,
) -> DecisionOptimizationEvent:
    return _make_event(
        OptimizationEventType.SOLUTION_SELECTED,
        request_id, decision_id, source,
        {"solution_id": solution_id, "rank": rank, "is_optimal": is_optimal},
    )


def make_solution_validated(
    request_id:   str,
    decision_id:  str,
    source:       str,
    *,
    is_valid:     bool = True,
    solution_id:  str  = "",
) -> DecisionOptimizationEvent:
    return _make_event(
        OptimizationEventType.SOLUTION_VALIDATED,
        request_id, decision_id, source,
        {"solution_id": solution_id, "is_valid": is_valid},
    )


def make_optimization_failed(
    request_id:  str,
    decision_id: str,
    source:      str,
    *,
    reason:      str = "",
) -> DecisionOptimizationEvent:
    return _make_event(
        OptimizationEventType.OPTIMIZATION_FAILED,
        request_id, decision_id, source,
        {"reason": reason},
    )
