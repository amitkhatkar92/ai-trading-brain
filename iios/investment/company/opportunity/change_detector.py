"""iios/investment/company/opportunity/change_detector.py
Detects material changes between consecutive opportunity evaluations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ChangeRecord:
    """A detected material change between two evaluations."""
    dimension:    str       # e.g. "overall_score", "lifecycle", "category"
    from_value:   str
    to_value:     str
    magnitude:    float     # absolute numeric change (0 if non-numeric)
    is_adverse:   bool      # True if the change is a negative signal
    detected_at:  datetime  = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension":   self.dimension,
            "from_value":  self.from_value,
            "to_value":    self.to_value,
            "magnitude":   round(self.magnitude, 2),
            "is_adverse":  self.is_adverse,
            "detected_at": self.detected_at.isoformat(),
        }


_SCORE_CHANGE_THRESHOLD = 5.0    # minimum score change to report
_COMPONENT_THRESHOLD    = 7.0    # minimum component score change to report


def detect_changes(
    current:  Dict[str, float],
    previous: Optional[Dict[str, float]],
) -> List[ChangeRecord]:
    """
    Detect material changes between *current* and *previous* score dictionaries.
    Both dicts map dimension name → numeric value.
    Returns a (possibly empty) list of ChangeRecords.
    """
    if previous is None:
        return []

    changes: List[ChangeRecord] = []
    all_keys = set(current) | set(previous)

    for key in all_keys:
        cur_v = current.get(key)
        prev_v = previous.get(key)
        if cur_v is None or prev_v is None:
            continue
        delta = cur_v - prev_v
        threshold = _SCORE_CHANGE_THRESHOLD if key == "overall_score" else _COMPONENT_THRESHOLD
        if abs(delta) >= threshold:
            changes.append(ChangeRecord(
                dimension=key,
                from_value=f"{prev_v:.1f}",
                to_value=f"{cur_v:.1f}",
                magnitude=abs(delta),
                is_adverse=delta < 0,
            ))

    return changes


def detect_lifecycle_change(
    current_lifecycle:  str,
    previous_lifecycle: Optional[str],
) -> Optional[ChangeRecord]:
    if previous_lifecycle is None or current_lifecycle == previous_lifecycle:
        return None
    # Adverse if moving to weakening/expired/archived
    adverse_states = {"weakening", "expired", "archived"}
    is_adverse = current_lifecycle in adverse_states
    return ChangeRecord(
        dimension="lifecycle",
        from_value=previous_lifecycle,
        to_value=current_lifecycle,
        magnitude=0.0,
        is_adverse=is_adverse,
    )


def detect_category_change(
    current_category:  str,
    previous_category: Optional[str],
) -> Optional[ChangeRecord]:
    if previous_category is None or current_category == previous_category:
        return None
    adverse_categories = {"observation_only", "watchlist"}
    is_adverse = current_category in adverse_categories
    return ChangeRecord(
        dimension="category",
        from_value=previous_category,
        to_value=current_category,
        magnitude=0.0,
        is_adverse=is_adverse,
    )


def score_dict_from_breakdown(breakdown: Any) -> Dict[str, float]:
    """
    Extract a flat score dictionary from an OpportunityScoreBreakdown for change detection.
    Accepts the breakdown object or None.
    """
    if breakdown is None:
        return {}
    result: Dict[str, float] = {}
    result["overall_score"] = getattr(breakdown, "final_score", 0.0)
    for comp in (getattr(breakdown, "components", lambda: []))():
        result[comp.name] = comp.score
    return result
