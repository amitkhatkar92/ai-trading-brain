"""iios/investment/company/earnings/revision_tracker.py
Tracks earnings revisions and computes revision-based signals.
Re-exports EarningsRevisionTracker for use in the engine.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.investment.company.earnings.earnings_revision import (
    EarningsRevisionTracker, EarningsRevisionEvent,
)


class RevisionSignal:
    """Derives analytical signals from revision history."""

    @staticmethod
    def revision_quality_score(
        tracker: EarningsRevisionTracker,
        ticker:  str,
    ) -> float:
        """
        Score from 0-100 based on revision history.
        100 = no revisions; <50 = frequent or sign-change revisions.
        """
        n = tracker.revision_count(ticker)
        if n == 0:
            return 100.0
        # Each revision costs 10 points; minimum 20
        score = max(20.0, 100.0 - n * 10.0)
        # Additional penalty for sign changes
        events = tracker.get_events(ticker)
        sign_changes = sum(1 for e in events if e.direction == "sign_change")
        score -= sign_changes * 15.0
        return max(0.0, min(100.0, score))

    @staticmethod
    def summary_dict(tracker: EarningsRevisionTracker, ticker: str) -> Dict[str, Any]:
        return tracker.summary(ticker)
