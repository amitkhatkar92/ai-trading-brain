"""iios/investment/decision/reasoning/hypothesis_registry.py
HypothesisRegistry — thread-safe registry of active hypotheses per decision.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.decision.reasoning.hypothesis_engine import Hypothesis
from iios.investment.decision.reasoning.reasoning_constants import HypothesisStatus, HypothesisType


class HypothesisRegistry:
    """Thread-safe per-decision hypothesis store."""

    def __init__(self) -> None:
        self._lock:   threading.RLock                    = threading.RLock()
        self._store:  Dict[str, List[Hypothesis]]         = {}   # decision_id → hypotheses

    def register(self, decision_id: str, hypotheses: List[Hypothesis]) -> None:
        with self._lock:
            self._store[decision_id] = list(hypotheses)

    def get_all(self, decision_id: str) -> List[Hypothesis]:
        with self._lock:
            return list(self._store.get(decision_id, []))

    def get_by_type(
        self,
        decision_id:    str,
        hypothesis_type: HypothesisType,
    ) -> Optional[Hypothesis]:
        with self._lock:
            for h in self._store.get(decision_id, []):
                if h.hypothesis_type == hypothesis_type:
                    return h
            return None

    def get_primary(self, decision_id: str) -> Optional[Hypothesis]:
        with self._lock:
            hypotheses = self._store.get(decision_id, [])
            supported = [h for h in hypotheses if h.status == HypothesisStatus.SUPPORTED]
            return max(supported, key=lambda h: h.support_score) if supported else None

    def known_decisions(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def count(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._store.values())

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "decisions": len(self._store),
                "total_hypotheses": self.count(),
            }
