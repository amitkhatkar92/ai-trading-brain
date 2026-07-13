"""iios/investment/company/integration/aggregation_state.py
Per-ticker mutable state container — stores the latest snapshot from each upstream engine.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.integration.company_state import (
    KNOWN_ENGINES, SCORED_ENGINES,
)


@dataclass
class EngineUpdate:
    """A single upstream snapshot with receipt metadata."""
    engine_name: str
    snapshot:    Any
    received_at: datetime
    sequence:    int = 0

    def age_seconds(self) -> float:
        """Seconds since this update was received."""
        return (datetime.now(timezone.utc) - self.received_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_name": self.engine_name,
            "received_at": self.received_at.isoformat(),
            "sequence":    self.sequence,
            "age_seconds": round(self.age_seconds(), 1),
        }


class AggregationState:
    """
    Thread-safe per-ticker container for the latest snapshot from each engine.
    Supports incremental updates — only one engine's data changes per call.
    """

    def __init__(self, ticker: str) -> None:
        self._lock         = threading.RLock()
        self.ticker        = ticker
        self.created_at    = datetime.now(timezone.utc)
        self._updates:     Dict[str, EngineUpdate] = {}
        self._sequence:    int = 0
        self._eval_count:  int = 0

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record_update(self, engine_name: str, snapshot: Any) -> EngineUpdate:
        """Store the latest snapshot from *engine_name*."""
        with self._lock:
            self._sequence += 1
            update = EngineUpdate(
                engine_name=engine_name,
                snapshot=snapshot,
                received_at=datetime.now(timezone.utc),
                sequence=self._sequence,
            )
            self._updates[engine_name] = update
            return update

    def increment_eval(self) -> int:
        with self._lock:
            self._eval_count += 1
            return self._eval_count

    # ── Read access ───────────────────────────────────────────────────────────

    def get_snapshot(self, engine_name: str) -> Optional[Any]:
        with self._lock:
            u = self._updates.get(engine_name)
            return u.snapshot if u else None

    def get_update(self, engine_name: str) -> Optional[EngineUpdate]:
        with self._lock:
            return self._updates.get(engine_name)

    def snapshot_map(self) -> Dict[str, Any]:
        """Return {engine_name: snapshot} for all received engines."""
        with self._lock:
            return {k: v.snapshot for k, v in self._updates.items()}

    def available_engines(self) -> List[str]:
        with self._lock:
            return list(self._updates.keys())

    def missing_engines(self) -> List[str]:
        with self._lock:
            return [e for e in KNOWN_ENGINES if e not in self._updates]

    def eval_count(self) -> int:
        with self._lock:
            return self._eval_count

    # ── Quality metrics ───────────────────────────────────────────────────────

    def completeness(self) -> float:
        """Fraction of SCORED_ENGINES (not including profile) that have data."""
        with self._lock:
            present = sum(1 for e in SCORED_ENGINES if e in self._updates)
            return present / len(SCORED_ENGINES)

    def last_update_at(self) -> Optional[datetime]:
        with self._lock:
            if not self._updates:
                return None
            return max(u.received_at for u in self._updates.values())

    def engine_ages(self) -> Dict[str, float]:
        """Seconds since each engine last provided data."""
        with self._lock:
            return {k: v.age_seconds() for k, v in self._updates.items()}

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "ticker":            self.ticker,
                "created_at":        self.created_at.isoformat(),
                "eval_count":        self._eval_count,
                "available_engines": self.available_engines(),
                "missing_engines":   self.missing_engines(),
                "completeness":      round(self.completeness(), 3),
                "updates":           {k: v.to_dict() for k, v in self._updates.items()},
            }
