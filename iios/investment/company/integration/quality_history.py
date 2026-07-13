"""iios/investment/company/integration/quality_history.py
Thread-safe ring buffer of QualityScore records per ticker.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


_DEFAULT_MAXLEN = 30


@dataclass
class QualityRecord:
    """A single quality assessment at a point in time."""
    ticker:           str
    captured_at:      datetime
    completeness:     float
    consistency:      float
    freshness:        float
    reliability:      float
    quality_score:    float   # 0-100
    confidence:       float   # 0-1
    conflict_count:   int
    available_engines: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":            self.ticker,
            "captured_at":       self.captured_at.isoformat(),
            "completeness":      round(self.completeness, 3),
            "consistency":       round(self.consistency, 3),
            "freshness":         round(self.freshness, 3),
            "reliability":       round(self.reliability, 3),
            "quality_score":     round(self.quality_score, 1),
            "confidence":        round(self.confidence, 3),
            "conflict_count":    self.conflict_count,
            "available_engines": self.available_engines,
        }


class QualityHistory:
    """Thread-safe per-ticker ring buffer of QualityRecord objects."""

    def __init__(self, maxlen: int = _DEFAULT_MAXLEN) -> None:
        self._lock   = threading.RLock()
        self._maxlen = maxlen
        self._store: Dict[str, deque] = {}

    def record(self, quality: QualityRecord) -> None:
        with self._lock:
            if quality.ticker not in self._store:
                self._store[quality.ticker] = deque(maxlen=self._maxlen)
            self._store[quality.ticker].append(quality)

    def get_history(self, ticker: str, n: int = 10) -> List[QualityRecord]:
        with self._lock:
            buf = self._store.get(ticker, deque())
            records = list(buf)
            return records[-n:][::-1]

    def latest(self, ticker: str) -> Optional[QualityRecord]:
        with self._lock:
            buf = self._store.get(ticker, deque())
            return buf[-1] if buf else None

    def quality_trend(self, ticker: str, n: int = 5) -> float:
        """Latest minus oldest quality score from last *n* records."""
        with self._lock:
            buf = self._store.get(ticker, deque())
            records = list(buf)[-n:]
            if len(records) < 2:
                return 0.0
            return records[-1].quality_score - records[0].quality_score

    def confidence_series(self, ticker: str, n: int = 5) -> List[float]:
        with self._lock:
            buf = self._store.get(ticker, deque())
            records = list(buf)[-n:]
            return [r.confidence for r in records]

    def known_tickers(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())
