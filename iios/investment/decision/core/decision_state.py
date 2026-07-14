"""iios/investment/decision/core/decision_state.py
DecisionState — mutable, thread-safe runtime state for one decision.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.decision.core.decision_constants import (
    VALID_TRANSITIONS,
    ApprovalStatus,
    DecisionStatus,
    RecommendationType,
    RiskReviewStatus,
)


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed by the state machine."""


class DecisionState:
    """
    Mutable, thread-safe container for the runtime state of a single decision.
    Enforces state-machine transitions via VALID_TRANSITIONS.
    """

    def __init__(self, decision_id: str) -> None:
        self._lock               = threading.RLock()
        self.decision_id         = decision_id
        self.status              = DecisionStatus.CREATED
        self.score               = 0.0
        self.confidence          = 0.0
        self.risk_review_status  = RiskReviewStatus.PENDING
        self.approval_status     = ApprovalStatus.PENDING
        self.recommendation:     Optional[RecommendationType] = None
        self.explanation         = ""
        self.error_message:      Optional[str]                = None
        self.phase_timestamps:   Dict[str, str]               = {
            DecisionStatus.CREATED.value: datetime.now(timezone.utc).isoformat()
        }

    # ----------------------------------------------------------------- transitions

    def transition_to(self, new_status: DecisionStatus) -> None:
        with self._lock:
            allowed = VALID_TRANSITIONS.get(self.status, set())
            if new_status not in allowed:
                raise InvalidTransitionError(
                    f"Cannot transition from {self.status.value!r} "
                    f"to {new_status.value!r}."
                )
            self.status = new_status
            self.phase_timestamps[new_status.value] = datetime.now(timezone.utc).isoformat()

    def fail(self, error: str = "") -> None:
        with self._lock:
            self.status        = DecisionStatus.FAILED
            self.error_message = error
            self.phase_timestamps[DecisionStatus.FAILED.value] = datetime.now(timezone.utc).isoformat()

    # ----------------------------------------------------------------- updaters

    def update_score(self, score: float, confidence: float = 0.0) -> None:
        with self._lock:
            self.score      = max(0.0, min(100.0, score))
            self.confidence = max(0.0, min(100.0, confidence))

    def update_risk_review(self, status: RiskReviewStatus) -> None:
        with self._lock:
            self.risk_review_status = status

    def update_recommendation(
        self,
        recommendation: RecommendationType,
        explanation:    str = "",
    ) -> None:
        with self._lock:
            self.recommendation = recommendation
            self.explanation    = explanation

    def update_approval(self, status: ApprovalStatus) -> None:
        with self._lock:
            self.approval_status = status

    # ----------------------------------------------------------------- accessors

    @property
    def is_failed(self) -> bool:
        return self.status == DecisionStatus.FAILED

    @property
    def phase_duration_seconds(self) -> Dict[str, float]:
        """Calculate duration between consecutive recorded phases."""
        ts_items = list(self.phase_timestamps.items())
        durations: Dict[str, float] = {}
        for i in range(1, len(ts_items)):
            prev_key, prev_ts = ts_items[i - 1]
            curr_key, curr_ts = ts_items[i]
            try:
                d = (datetime.fromisoformat(curr_ts) - datetime.fromisoformat(prev_ts)).total_seconds()
                durations[f"{prev_key}_to_{curr_key}"] = round(d, 3)
            except (ValueError, TypeError):
                pass
        return durations

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "decision_id":        self.decision_id,
                "status":             self.status.value,
                "score":              round(self.score, 2),
                "confidence":         round(self.confidence, 2),
                "risk_review_status": self.risk_review_status.value,
                "approval_status":    self.approval_status.value,
                "recommendation":     self.recommendation.value if self.recommendation else None,
                "explanation":        self.explanation,
                "error_message":      self.error_message,
                "phase_timestamps":   dict(self.phase_timestamps),
            }
