"""iios/investment/company/profile/geographic_presence.py
Geographic exposure and operations tracking.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from iios.investment.company.profile.models import GeographicPresence, OperationsType


class GeographicPresenceStore:
    """Manages geographic exposures for one company."""

    def __init__(self) -> None:
        self._presences: List[GeographicPresence] = []

    def add(self, presence: GeographicPresence) -> None:
        # Replace if same country + ops_type
        self._presences = [
            p for p in self._presences
            if not (p.country == presence.country
                    and p.operations_type is presence.operations_type)
        ]
        self._presences.append(presence)

    def remove(self, country: str) -> bool:
        before = len(self._presences)
        self._presences = [p for p in self._presences if p.country != country]
        return len(self._presences) < before

    def all(self) -> List[GeographicPresence]:
        return sorted(self._presences, key=lambda p: p.revenue_pct, reverse=True)

    def by_region(self) -> Dict[str, List[GeographicPresence]]:
        result: Dict[str, List[GeographicPresence]] = defaultdict(list)
        for p in self._presences:
            result[p.region].append(p)
        return dict(result)

    def by_operations_type(self, ops_type: OperationsType) -> List[GeographicPresence]:
        return [p for p in self._presences if p.operations_type is ops_type]

    def top_countries(self, n: int = 5) -> List[GeographicPresence]:
        return sorted(self._presences, key=lambda p: p.revenue_pct, reverse=True)[:n]

    def total_revenue_pct(self) -> float:
        return sum(p.revenue_pct for p in self._presences)

    def countries(self) -> List[str]:
        return sorted({p.country for p in self._presences})

    def regions(self) -> List[str]:
        return sorted({p.region for p in self._presences})

    def domestic_pct(self, home_country: str) -> float:
        """Revenue % from home country."""
        return sum(
            p.revenue_pct for p in self._presences
            if p.country.upper() == home_country.upper()
        )

    def international_pct(self, home_country: str) -> float:
        return max(0.0, 100.0 - self.domestic_pct(home_country))

    def is_domestic_only(self, home_country: str) -> bool:
        return len(self._presences) == 1 and self.domestic_pct(home_country) > 0

    def __len__(self) -> int:
        return len(self._presences)
