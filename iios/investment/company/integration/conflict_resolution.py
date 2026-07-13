"""iios/investment/company/integration/conflict_resolution.py
Deterministic conflict resolution strategies.
"""
from __future__ import annotations

from typing import Any, List, Optional

from iios.investment.company.integration.company_state import (
    ConflictSeverity, ConflictStatus, ConflictType, ResolutionStrategy,
)
from iios.investment.company.integration.conflict_detector import ConflictRecord


# ── Engine confidence weights (for trust-based resolution) ───────────────────

_ENGINE_CONFIDENCE: dict = {
    "financials":       0.90,   # Most objective; audited data
    "earnings":         0.85,
    "business_quality": 0.80,
    "valuation":        0.70,   # Model-dependent; lower trust
    "growth":           0.75,
    "management":       0.65,
    "ownership":        0.70,
    "opportunity":      0.60,   # Composite of all — penalise circularity
}


def _trust(engine: str) -> float:
    return _ENGINE_CONFIDENCE.get(engine, 0.50)


# ── Resolution strategies ─────────────────────────────────────────────────────

def resolve_by_higher_confidence(
    conflict: ConflictRecord,
    intel: Any = None,
) -> Optional[str]:
    """Trust the engine with higher inherent confidence."""
    ta = _trust(conflict.engine_a)
    tb = _trust(conflict.engine_b)
    if abs(ta - tb) < 0.05:
        return None  # Too close to call deterministically
    winner = conflict.engine_a if ta > tb else conflict.engine_b
    return f"Resolved by confidence: trusting {winner} (confidence={max(ta, tb):.2f})"


def resolve_by_conservative(
    conflict: ConflictRecord,
    intel: Any = None,
) -> Optional[str]:
    """
    For risk-type conflicts, adopt the more cautious (pessimistic) view.
    """
    if conflict.conflict_type not in (
        ConflictType.RISK_CONFLICT, ConflictType.SIGNAL_CONFLICT
    ):
        return None
    return (
        f"Resolved conservatively: adopting the more cautious signal between "
        f"{conflict.engine_a} and {conflict.engine_b}."
    )


def resolve_by_latest_update(
    conflict: ConflictRecord,
    ages: Optional[dict] = None,
) -> Optional[str]:
    """Trust the most recently updated engine."""
    if ages is None:
        return None
    age_a = ages.get(conflict.engine_a)
    age_b = ages.get(conflict.engine_b)
    if age_a is None or age_b is None:
        return None
    winner = conflict.engine_a if age_a < age_b else conflict.engine_b
    return f"Resolved by recency: trusting {winner} (most recently updated)."


# ── Conflict resolver orchestrator ────────────────────────────────────────────

class ConflictResolver:
    """
    Applies resolution strategies to a list of ConflictRecord objects.

    Strategy cascade (in order):
    1. Higher confidence engine
    2. Conservative for risk/signal conflicts
    3. Latest update
    4. Escalate if none resolved
    """

    def resolve_all(
        self,
        conflicts: List[ConflictRecord],
        intel: Any = None,
        engine_ages: Optional[dict] = None,
    ) -> List[ConflictRecord]:
        """Attempt to resolve every unresolved conflict."""
        for conflict in conflicts:
            if conflict.status != ConflictStatus.DETECTED:
                continue
            self._resolve_one(conflict, intel, engine_ages)
        return conflicts

    def _resolve_one(
        self,
        conflict: ConflictRecord,
        intel: Any,
        engine_ages: Optional[dict],
    ) -> None:
        resolution: Optional[str] = None

        # Strategy 1: higher confidence
        resolution = resolve_by_higher_confidence(conflict, intel)

        # Strategy 2: conservative (for risk/signal)
        if resolution is None:
            resolution = resolve_by_conservative(conflict, intel)

        # Strategy 3: latest update
        if resolution is None:
            resolution = resolve_by_latest_update(conflict, engine_ages)

        if resolution is not None:
            conflict.status     = ConflictStatus.RESOLVED
            conflict.resolution = resolution
        elif conflict.severity in (ConflictSeverity.CRITICAL, ConflictSeverity.HIGH):
            conflict.status     = ConflictStatus.ESCALATED
            conflict.resolution = (
                f"Escalated: no deterministic resolution for "
                f"{conflict.engine_a} vs {conflict.engine_b}."
            )
        else:
            conflict.status     = ConflictStatus.DISMISSED
            conflict.resolution = "Dismissed: low-severity conflict; insufficient basis for resolution."
