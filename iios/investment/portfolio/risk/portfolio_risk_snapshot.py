"""iios/investment/portfolio/risk/portfolio_risk_snapshot.py

Lightweight risk record and bounded thread-safe risk history.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.risk.portfolio_risk_profile import PortfolioRiskProfile


@dataclass(frozen=True)
class RiskRecord:
    """Lightweight immutable audit record of a risk evaluation."""

    record_id:       str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:    str   = ""
    plan_id:         str   = ""
    profile_id:      str   = ""
    created_at:      str   = ""

    overall_risk_score: float = 0.0
    risk_grade:         str   = "B"
    risk_level:         str   = "moderate"
    is_acceptable:      bool  = True
    n_alerts:           int   = 0
    n_critical_alerts:  int   = 0
    confidence_score:   float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id":       self.record_id,
            "portfolio_id":    self.portfolio_id,
            "created_at":      self.created_at,
            "overall_risk_score": round(self.overall_risk_score, 4),
            "risk_grade":      self.risk_grade,
            "risk_level":      self.risk_level,
            "is_acceptable":   self.is_acceptable,
        }

    @classmethod
    def from_profile(cls, profile: PortfolioRiskProfile) -> "RiskRecord":
        return cls(
            portfolio_id     = profile.portfolio_id,
            plan_id          = profile.plan_id,
            profile_id       = profile.profile_id,
            created_at       = profile.created_at,
            overall_risk_score = profile.overall_risk_score,
            risk_grade       = profile.risk_grade,
            risk_level       = profile.risk_level,
            is_acceptable    = profile.is_acceptable,
            n_alerts         = profile.n_alerts,
            n_critical_alerts= profile.n_critical_alerts,
            confidence_score = profile.confidence_score,
        )


class RiskHistory:
    """Thread-safe bounded history of RiskRecord entries."""

    def __init__(self, portfolio_id: str, max_snapshots: int = 200) -> None:
        self._portfolio_id = portfolio_id
        self._max          = max_snapshots
        self._lock         = threading.RLock()
        self._records:     List[RiskRecord] = []

    def record(self, profile: PortfolioRiskProfile) -> None:
        with self._lock:
            self._records.append(RiskRecord.from_profile(profile))
            if len(self._records) > self._max:
                self._records = self._records[-self._max:]

    def latest(self) -> Optional[RiskRecord]:
        with self._lock:
            return self._records[-1] if self._records else None

    def all(self, n: Optional[int] = None) -> List[RiskRecord]:
        with self._lock:
            if n is None:
                return list(self._records)
            return list(self._records[-n:])

    def best(self) -> Optional[RiskRecord]:
        with self._lock:
            if not self._records:
                return None
            return min(self._records, key=lambda r: r.overall_risk_score)
