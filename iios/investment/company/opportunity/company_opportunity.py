"""iios/investment/company/opportunity/company_opportunity.py
CompanyOpportunity — persistent per-ticker state maintained by the engine.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.opportunity.opportunity_lifecycle import LifecycleChange
from iios.investment.company.opportunity.opportunity_profile import (
    OpportunityCategory, OpportunityLifecycle, OpportunityPriority,
    WatchlistEntry,
)


_SCORE_HISTORY_DEPTH = 20    # rolling window for trend computation


@dataclass
class CompanyOpportunity:
    """
    Mutable state object maintained per ticker across evaluation cycles.
    Stores history, lifecycle changes, watchlist status, and metadata.
    NOT a snapshot — it is the registry entry that snapshots are derived from.
    """
    ticker:           str
    opportunity_id:   str
    discovery_time:   datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lifecycle_state:  OpportunityLifecycle = OpportunityLifecycle.DISCOVERED
    priority:         OpportunityPriority  = OpportunityPriority.LOW
    primary_category: OpportunityCategory  = OpportunityCategory.UNCLASSIFIED

    # Rolling score deque (last N scores for trend computation)
    _score_history: deque = field(
        default_factory=lambda: deque(maxlen=_SCORE_HISTORY_DEPTH), repr=False
    )
    _lifecycle_changes: List[LifecycleChange] = field(default_factory=list, repr=False)

    # Company metadata
    company_name: Optional[str] = None
    sector:       Optional[str] = None
    industry:     Optional[str] = None
    exchange:     Optional[str] = None

    # Watchlist
    watchlist_entry: Optional[WatchlistEntry] = None

    # Tags for custom grouping
    custom_tags: List[str] = field(default_factory=list)

    # Last computed evaluation data (for change detection in monitor)
    last_snapshot: Any = field(default=None, repr=False)
    evaluation_count: int = 0

    # ── Score history helpers ─────────────────────────────────────────────────

    def record_score(self, score: float) -> None:
        self._score_history.append(score)

    @property
    def score_history(self) -> List[float]:
        return list(self._score_history)

    @property
    def score_trend(self) -> float:
        """
        Linear trend of the score over the stored history.
        Positive = improving, negative = deteriorating.
        """
        history = list(self._score_history)
        n = len(history)
        if n < 2:
            return 0.0
        # Simple last-vs-first-half comparison
        half = max(1, n // 2)
        recent_avg = sum(history[-half:]) / half
        older_avg  = sum(history[:half]) / half
        return recent_avg - older_avg

    @property
    def latest_score(self) -> Optional[float]:
        history = list(self._score_history)
        return history[-1] if history else None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def add_lifecycle_change(self, change: LifecycleChange) -> None:
        self._lifecycle_changes.append(change)
        # Keep last 30 transitions
        if len(self._lifecycle_changes) > 30:
            self._lifecycle_changes = self._lifecycle_changes[-30:]

    @property
    def lifecycle_history(self) -> List[LifecycleChange]:
        return list(self._lifecycle_changes)

    @property
    def days_since_discovery(self) -> float:
        delta = datetime.now(timezone.utc) - self.discovery_time
        return delta.total_seconds() / 86400.0

    # ── Watchlist ─────────────────────────────────────────────────────────────

    @property
    def is_watchlisted(self) -> bool:
        return self.watchlist_entry is not None

    def add_to_watchlist(self, notes: str = "", tags: Optional[List[str]] = None) -> None:
        self.watchlist_entry = WatchlistEntry(
            ticker=self.ticker,
            added_at=datetime.now(timezone.utc),
            notes=notes,
            tags=tags or [],
        )

    def remove_from_watchlist(self) -> None:
        self.watchlist_entry = None

    # ── Tags ──────────────────────────────────────────────────────────────────

    def add_tag(self, tag: str) -> None:
        if tag not in self.custom_tags:
            self.custom_tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        self.custom_tags = [t for t in self.custom_tags if t != tag]

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":           self.ticker,
            "opportunity_id":   self.opportunity_id,
            "discovery_time":   self.discovery_time.isoformat(),
            "lifecycle_state":  self.lifecycle_state.value,
            "priority":         self.priority.value,
            "primary_category": self.primary_category.value,
            "company_name":     self.company_name,
            "sector":           self.sector,
            "industry":         self.industry,
            "exchange":         self.exchange,
            "is_watchlisted":   self.is_watchlisted,
            "custom_tags":      self.custom_tags,
            "evaluation_count": self.evaluation_count,
            "latest_score":     self.latest_score,
            "score_trend":      round(self.score_trend, 2),
            "days_since_discovery": round(self.days_since_discovery, 1),
        }
