"""iios/investment/market/opportunity/ranking_history.py
Ring buffer storing per-bar ranking snapshots.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, Iterator, List, Optional

from iios.investment.market.opportunity.models import RankingScore


class RankingHistory:
    """Stores dicts of {opportunity_id: RankingScore} per bar."""

    def __init__(self, maxlen: int = 100) -> None:
        self._buffer: deque[Dict[str, RankingScore]] = deque(maxlen=maxlen)

    def append(self, scores: Dict[str, RankingScore]) -> None:
        self._buffer.append(dict(scores))

    def latest(self) -> Optional[Dict[str, RankingScore]]:
        return self._buffer[-1] if self._buffer else None

    def recent(self, n: int) -> List[Dict[str, RankingScore]]:
        return list(self._buffer)[-n:]

    def symbol_series(self, opportunity_id: str, n: int) -> List[float]:
        """Composite score time series for one opportunity (oldest first)."""
        return [
            frame[opportunity_id].composite_score
            for frame in list(self._buffer)[-n:]
            if opportunity_id in frame
        ]

    def __len__(self) -> int:
        return len(self._buffer)
