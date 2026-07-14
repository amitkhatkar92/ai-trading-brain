"""iios/investment/decision/integration/aggregation_state.py
AggregationState — thread-safe mutable container for all upstream snapshots
belonging to a single decision_id.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot

from iios.investment.decision.integration.integration_constants import (
    ComponentId,
    COMPONENT_MAX_AGE_SECONDS,
)


class AggregationState:
    """
    Mutable, thread-safe container that holds every upstream snapshot for one
    decision.  Updated incrementally as engines publish results.
    """

    __slots__ = (
        "_lock", "decision_id", "subject_id", "subject_type",
        "evidence", "reasoning", "confidence", "risk",
        "explanation", "committee", "recommendation",
        "version", "created_at", "last_updated",
    )

    def __init__(self, decision_id: str, subject_id: str, subject_type: str) -> None:
        self._lock      = threading.RLock()
        self.decision_id   = decision_id
        self.subject_id    = subject_id
        self.subject_type  = subject_type
        self.evidence:       Optional[EvidenceSnapshot]     = None
        self.reasoning:      Optional[ReasoningSnapshot]    = None
        self.confidence:     Optional[ConfidenceSnapshot]   = None
        self.risk:           Optional[RiskSnapshot]         = None
        self.explanation:    Optional[ExplanationSnapshot]  = None
        self.committee:      Optional[Any]                  = None  # CommitteeReport
        self.recommendation: Optional[Any]                  = None  # RecommendationSnapshot
        self.version    = 0
        self.created_at = datetime.now(timezone.utc)
        self.last_updated = self.created_at

    # ── Mutators ──────────────────────────────────────────────────────────────

    def update(self, component: ComponentId, value: Any) -> None:
        with self._lock:
            setattr(self, component.value, value)
            self.version     += 1
            self.last_updated = datetime.now(timezone.utc)

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def present_components(self) -> frozenset:
        with self._lock:
            result = set()
            for c in ComponentId:
                if getattr(self, c.value, None) is not None:
                    result.add(c)
            return frozenset(result)

    @property
    def required_present(self) -> frozenset:
        return self.present_components & ComponentId.required()

    @property
    def completeness(self) -> float:
        """Fraction of REQUIRED components that are present (0–1)."""
        req = ComponentId.required()
        present = len(self.required_present)
        return present / len(req) if req else 0.0

    @property
    def is_complete(self) -> bool:
        return self.required_present == ComponentId.required()

    @property
    def age_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.last_updated).total_seconds()

    @property
    def is_stale(self) -> bool:
        return self.age_seconds > COMPONENT_MAX_AGE_SECONDS

    def snapshot(self) -> "_AggregationStateSnapshot":
        """Return an immutable copy of the current state."""
        with self._lock:
            return _AggregationStateSnapshot(
                decision_id    = self.decision_id,
                subject_id     = self.subject_id,
                subject_type   = self.subject_type,
                evidence       = self.evidence,
                reasoning      = self.reasoning,
                confidence     = self.confidence,
                risk           = self.risk,
                explanation    = self.explanation,
                committee      = self.committee,
                recommendation = self.recommendation,
                version        = self.version,
                created_at     = self.created_at,
                last_updated   = self.last_updated,
            )

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "decision_id":          self.decision_id,
                "subject_id":           self.subject_id,
                "subject_type":         self.subject_type,
                "version":              self.version,
                "completeness":         round(self.completeness, 3),
                "is_complete":          self.is_complete,
                "is_stale":             self.is_stale,
                "present_components":   [c.value for c in self.present_components],
                "missing_required":     [
                    c.value for c in ComponentId.required()
                    if c not in self.required_present
                ],
                "last_updated":         self.last_updated.isoformat(),
            }


class _AggregationStateSnapshot:
    """Immutable point-in-time copy of AggregationState."""

    __slots__ = (
        "decision_id", "subject_id", "subject_type",
        "evidence", "reasoning", "confidence", "risk",
        "explanation", "committee", "recommendation",
        "version", "created_at", "last_updated",
    )

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("_AggregationStateSnapshot is immutable")

    @property
    def completeness(self) -> float:
        req = ComponentId.required()
        present = sum(1 for c in req if getattr(self, c.value, None) is not None)
        return present / len(req) if req else 0.0

    @property
    def is_complete(self) -> bool:
        return all(getattr(self, c.value, None) is not None for c in ComponentId.required())

    @property
    def present_components(self) -> frozenset:
        return frozenset(c for c in ComponentId if getattr(self, c.value, None) is not None)

    @property
    def required_present(self) -> frozenset:
        return self.present_components & ComponentId.required()
