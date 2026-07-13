"""iios/investment/company/profile/business_segments.py
Business segment management for a company's business profile.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.profile.models import BusinessSegment


class SegmentStore:
    """Manages revenue segments for one company."""

    def __init__(self) -> None:
        self._segments: List[BusinessSegment] = []

    def add(self, segment: BusinessSegment) -> None:
        self._segments = [s for s in self._segments if s.name != segment.name]
        self._segments.append(segment)
        self._normalise_primary()

    def remove(self, name: str) -> bool:
        before = len(self._segments)
        self._segments = [s for s in self._segments if s.name != name]
        return len(self._segments) < before

    def primary(self) -> Optional[BusinessSegment]:
        primary = [s for s in self._segments if s.is_primary]
        if primary:
            return primary[0]
        if self._segments:
            return max(self._segments, key=lambda s: s.revenue_pct)
        return None

    def all(self) -> List[BusinessSegment]:
        return sorted(self._segments, key=lambda s: s.revenue_pct, reverse=True)

    def total_revenue_pct(self) -> float:
        return sum(s.revenue_pct for s in self._segments)

    def is_balanced(self, tolerance: float = 5.0) -> bool:
        """Return True if segments sum to ~100% within tolerance."""
        total = self.total_revenue_pct()
        return abs(total - 100.0) <= tolerance

    def _normalise_primary(self) -> None:
        """Ensure at most one segment is marked primary."""
        primaries = [s for s in self._segments if s.is_primary]
        if len(primaries) > 1:
            # Keep the one with highest revenue_pct as primary
            top = max(primaries, key=lambda s: s.revenue_pct)
            for s in primaries:
                if s is not top:
                    s.is_primary = False

    def __len__(self) -> int:
        return len(self._segments)
