"""iios/investment/market/integration/conflict_history.py
Ring buffer of ConflictSummary objects.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional

from iios.investment.market.integration.models import ConflictSeverity, ConflictSummary


class ConflictHistory:
    """Fixed-length history of ConflictSummary, newest last."""

    def __init__(self, maxlen: int = 200) -> None:
        self._buf: Deque[ConflictSummary] = deque(maxlen=maxlen)

    def append(self, summary: ConflictSummary) -> None:
        self._buf.append(summary)

    def latest(self) -> Optional[ConflictSummary]:
        return self._buf[-1] if self._buf else None

    def recent(self, n: int) -> List[ConflictSummary]:
        items = list(self._buf)
        return items[-n:] if n < len(items) else items

    def total_series(self, n: int) -> List[int]:
        return [s.total for s in self.recent(n)]

    def critical_series(self, n: int) -> List[int]:
        return [s.critical for s in self.recent(n)]

    def unresolved_series(self, n: int) -> List[int]:
        return [s.unresolved for s in self.recent(n)]

    def has_persistent_critical(self, n: int = 3) -> bool:
        """Return True if every recent bar had at least one CRITICAL conflict."""
        series = self.critical_series(n)
        return len(series) == n and all(c > 0 for c in series)

    def __len__(self) -> int:
        return len(self._buf)
