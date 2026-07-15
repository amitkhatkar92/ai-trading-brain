"""iios/investment/portfolio/recommendation/recommendation_expiration.py

Expiration management for portfolio recommendations.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Any

from iios.investment.portfolio.recommendation.recommendation_types import (
    RecommendationPriority, priority_to_expiry_hours, now_utc,
)
from iios.investment.portfolio.recommendation.recommendation_policies import PolicyParameters


def compute_expires_at(
    priority:  RecommendationPriority,
    params:    PolicyParameters,
    from_time: Optional[str] = None,
) -> str:
    """
    Compute the expiry timestamp for a recommendation.

    Parameters
    ----------
    priority   : recommendation priority
    params     : policy parameters controlling expiry hours
    from_time  : base ISO timestamp; defaults to now_utc()

    Returns
    -------
    ISO timestamp string for expiry
    """
    hours = priority_to_expiry_hours(
        priority,
        critical_hours  = params.critical_expiry_hours,
        high_hours      = params.high_expiry_hours,
        default_hours   = params.default_expiry_hours,
        low_hours       = params.low_expiry_hours,
        no_action_hours = params.no_action_expiry_hours,
    )
    base = datetime.fromisoformat(from_time) if from_time else datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return (base + timedelta(hours=hours)).isoformat()


def is_expired(rec: Any) -> bool:
    """Return True if the recommendation has passed its expiry timestamp."""
    expires_at = getattr(rec, "expires_at", None)
    if not expires_at:
        return False
    try:
        exp = datetime.fromisoformat(expires_at)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > exp
    except (ValueError, TypeError):
        return False


def filter_expired(recommendations: List[Any]) -> List[Any]:
    """Remove expired recommendations from a list."""
    return [r for r in recommendations if not is_expired(r)]


def hours_remaining(rec: Any) -> float:
    """Return hours remaining until expiry; 0 if already expired."""
    expires_at = getattr(rec, "expires_at", None)
    if not expires_at:
        return 0.0
    try:
        exp = datetime.fromisoformat(expires_at)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        delta = exp - datetime.now(timezone.utc)
        return max(0.0, delta.total_seconds() / 3600.0)
    except (ValueError, TypeError):
        return 0.0
