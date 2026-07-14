"""iios/investment/portfolio/diversification/diversification_snapshot.py

Lightweight snapshot + bounded history for one portfolio.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.diversification.diversification_profile import DiversificationProfile
from iios.investment.portfolio.diversification.diversification_types import (
    DiversificationGrade,
    DIVERSIFICATION_SNAPSHOT_SCHEMA_VERSION,
)


@dataclass(frozen=True)
class DiversificationRecord:
    """Lightweight audit record alongside each profile."""

    record_id:     str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:  str   = ""
    profile_id:    str   = ""
    plan_id:       str   = ""
    version:       int   = 1
    n_positions:   int   = 0
    hhi:           float = 0.0
    effective_n:   float = 0.0
    overall_score: float = 0.0
    grade:         str   = "F"
    is_acceptable: bool  = False
    n_alerts:      int   = 0
    n_critical_alerts: int = 0
    created_at:    float = 0.0
    recorded_at:   float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":       self.record_id,
            "portfolio_id":    self.portfolio_id,
            "profile_id":      self.profile_id,
            "plan_id":         self.plan_id,
            "version":         self.version,
            "n_positions":     self.n_positions,
            "hhi":             round(self.hhi, 6),
            "effective_n":     round(self.effective_n, 2),
            "overall_score":   round(self.overall_score, 4),
            "grade":           self.grade,
            "is_acceptable":   self.is_acceptable,
            "n_alerts":        self.n_alerts,
            "n_critical_alerts":self.n_critical_alerts,
            "created_at":      self.created_at,
            "recorded_at":     self.recorded_at,
        }


class DiversificationHistory:
    """Thread-safe, bounded per-portfolio history of DiversificationProfiles."""

    def __init__(self, portfolio_id: str, max_snapshots: int = 200) -> None:
        self._portfolio_id  = portfolio_id
        self._max_snapshots = max(1, max_snapshots)
        self._profiles: List[DiversificationProfile] = []
        self._records:  List[DiversificationRecord]  = []
        self._lock = threading.RLock()

    def record(self, profile: DiversificationProfile) -> DiversificationRecord:
        rec = DiversificationRecord(
            portfolio_id    = profile.portfolio_id,
            profile_id      = profile.profile_id,
            plan_id         = profile.plan_id,
            version         = profile.version,
            n_positions     = profile.n_positions,
            hhi             = profile.hhi,
            effective_n     = profile.effective_n,
            overall_score   = profile.overall_score,
            grade           = profile.grade.value,
            is_acceptable   = profile.is_acceptable,
            n_alerts        = profile.n_alerts,
            n_critical_alerts=profile.n_critical_alerts,
            created_at      = profile.created_at,
        )
        with self._lock:
            self._profiles.append(profile)
            self._records.append(rec)
            if len(self._profiles) > self._max_snapshots:
                self._profiles.pop(0)
                self._records.pop(0)
        return rec

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    def count(self) -> int:
        with self._lock:
            return len(self._profiles)

    def latest(self) -> Optional[DiversificationProfile]:
        with self._lock:
            return self._profiles[-1] if self._profiles else None

    def latest_record(self) -> Optional[DiversificationRecord]:
        with self._lock:
            return self._records[-1] if self._records else None

    def best(self) -> Optional[DiversificationProfile]:
        with self._lock:
            return max(self._profiles, key=lambda p: p.overall_score) if self._profiles else None

    def recent(self, n: int = 10) -> List[DiversificationProfile]:
        with self._lock:
            return list(self._profiles[-n:])

    def all_profiles(self) -> List[DiversificationProfile]:
        with self._lock:
            return list(self._profiles)

    def all_records(self) -> List[DiversificationRecord]:
        with self._lock:
            return list(self._records)

    def metric_series(self, metric: str) -> List[float]:
        """Extract a time-ordered list of values for a named metric."""
        with self._lock:
            profiles = list(self._profiles)
        result = []
        for p in profiles:
            val = getattr(p, metric, None)
            if val is not None and isinstance(val, (int, float)):
                result.append(float(val))
        return result

    def reset(self) -> None:
        with self._lock:
            self._profiles.clear()
            self._records.clear()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "portfolio_id":  self._portfolio_id,
                "max_snapshots": self._max_snapshots,
                "count":         len(self._profiles),
                "records":       [r.to_dict() for r in self._records],
            }
