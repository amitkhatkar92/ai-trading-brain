"""iios/investment/strategy/evaluation/equity_curve.py
EquityCurve — ordered sequence of (timestamp, portfolio_value) points.
Used as input to all performance and risk sub-engines.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class EquityPoint:
    timestamp: datetime
    value: float


@dataclass
class EquityCurve:
    """Sorted time-series of equity values.  Immutable after construction."""

    points: List[EquityPoint] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.points = sorted(self.points, key=lambda p: p.timestamp)

    # ── basic accessors ─────────────────────────────────────────────────────

    @property
    def values(self) -> List[float]:
        return [p.value for p in self.points]

    @property
    def timestamps(self) -> List[datetime]:
        return [p.timestamp for p in self.points]

    @property
    def start_value(self) -> float:
        return self.points[0].value if self.points else 0.0

    @property
    def end_value(self) -> float:
        return self.points[-1].value if self.points else 0.0

    @property
    def length(self) -> int:
        return len(self.points)

    def is_empty(self) -> bool:
        return len(self.points) < 2

    # ── derived returns ─────────────────────────────────────────────────────

    @property
    def period_returns(self) -> List[float]:
        """Period-over-period arithmetic returns."""
        vals = self.values
        if len(vals) < 2:
            return []
        result = []
        for i in range(1, len(vals)):
            prev = vals[i - 1]
            result.append((vals[i] - prev) / prev if prev != 0.0 else 0.0)
        return result

    @property
    def log_returns(self) -> List[float]:
        """Log returns; safe for zero/negative values (clamp to near-zero)."""
        vals = self.values
        if len(vals) < 2:
            return []
        result = []
        for i in range(1, len(vals)):
            prev = vals[i - 1]
            cur = vals[i]
            if prev > 0.0 and cur > 0.0:
                result.append(math.log(cur / prev))
            else:
                result.append(0.0)
        return result

    @property
    def total_return(self) -> float:
        if self.start_value == 0.0:
            return 0.0
        return (self.end_value - self.start_value) / self.start_value

    @property
    def duration_years(self) -> float:
        if len(self.points) < 2:
            return 0.0
        delta = self.points[-1].timestamp - self.points[0].timestamp
        return delta.total_seconds() / (365.25 * 86_400)

    # ── peaks and drawdowns ─────────────────────────────────────────────────

    def running_peak(self) -> List[float]:
        """Running maximum value at each point."""
        if not self.points:
            return []
        peaks, cur_peak = [], self.points[0].value
        for p in self.points:
            cur_peak = max(cur_peak, p.value)
            peaks.append(cur_peak)
        return peaks

    def drawdown_series(self) -> List[float]:
        """Drawdown at each point as a fraction (0 = no dd, 0.20 = 20% dd)."""
        peaks = self.running_peak()
        result = []
        for pk, pt in zip(peaks, self.points):
            dd = (pk - pt.value) / pk if pk > 0.0 else 0.0
            result.append(dd)
        return result

    # ── slicing ─────────────────────────────────────────────────────────────

    def slice(self, start: datetime, end: datetime) -> "EquityCurve":
        return EquityCurve(
            [p for p in self.points if start <= p.timestamp <= end]
        )

    def halves(self) -> Tuple["EquityCurve", "EquityCurve"]:
        mid = len(self.points) // 2
        return (
            EquityCurve(self.points[:mid]),
            EquityCurve(self.points[mid:]),
        )

    # ── factory ─────────────────────────────────────────────────────────────

    @classmethod
    def from_values(
        cls, values: List[float], start: Optional[datetime] = None
    ) -> "EquityCurve":
        """Build from a plain list of values at daily frequency."""
        from datetime import timedelta
        base = start or datetime(2000, 1, 1, tzinfo=timezone.utc)
        pts = [
            EquityPoint(timestamp=base + timedelta(days=i), value=v)
            for i, v in enumerate(values)
        ]
        return cls(pts)
