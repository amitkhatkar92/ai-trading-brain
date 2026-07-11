"""iios/investment/market/integration/quality_history.py
Ring buffer of QualityScore objects.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional

from iios.investment.market.integration.models import QualityScore


class QualityHistory:
    """Fixed-length history of QualityScore, newest last."""

    def __init__(self, maxlen: int = 200) -> None:
        self._buf: Deque[QualityScore] = deque(maxlen=maxlen)

    def append(self, score: QualityScore) -> None:
        self._buf.append(score)

    def latest(self) -> Optional[QualityScore]:
        return self._buf[-1] if self._buf else None

    def recent(self, n: int) -> List[QualityScore]:
        items = list(self._buf)
        return items[-n:] if n < len(items) else items

    def overall_series(self, n: int) -> List[float]:
        return [s.overall for s in self.recent(n)]

    def completeness_series(self, n: int) -> List[float]:
        return [s.completeness for s in self.recent(n)]

    def consistency_series(self, n: int) -> List[float]:
        return [s.consistency for s in self.recent(n)]

    def __len__(self) -> int:
        return len(self._buf)
