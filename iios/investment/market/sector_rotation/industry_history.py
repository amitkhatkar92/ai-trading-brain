"""iios/investment/market/sector_rotation/industry_history.py
Ring buffer storing per-bar IndustryProfile snapshots for replay and analysis.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, Iterator, List, Optional

from iios.investment.market.sector_rotation.models import IndustryProfile


class IndustryHistory:
    """Stores sequential dicts of ``{industry: IndustryProfile}`` (newest last)."""

    def __init__(self, maxlen: int = 250) -> None:
        self._buffer: deque[Dict[str, IndustryProfile]] = deque(maxlen=maxlen)

    def append(self, profiles: Dict[str, IndustryProfile]) -> None:
        self._buffer.append(dict(profiles))

    def latest(self) -> Optional[Dict[str, IndustryProfile]]:
        return self._buffer[-1] if self._buffer else None

    def recent(self, n: int) -> List[Dict[str, IndustryProfile]]:
        return list(self._buffer)[-n:]

    def industry_series(self, industry: str, n: int) -> List[IndustryProfile]:
        """Time series for one industry over last n bars (oldest first)."""
        return [
            frame[industry]
            for frame in list(self._buffer)[-n:]
            if industry in frame
        ]

    def __len__(self) -> int:
        return len(self._buffer)
