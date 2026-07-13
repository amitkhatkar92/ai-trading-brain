"""iios/investment/company/profile/subsidiaries.py
Subsidiary and controlled entity management.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.investment.company.profile.models import RelationshipType, Subsidiary


class SubsidiaryStore:
    """Manages subsidiary entities for one company."""

    def __init__(self) -> None:
        self._subs: List[Subsidiary] = []

    def add(self, subsidiary: Subsidiary) -> None:
        self._subs = [s for s in self._subs if s.name != subsidiary.name]
        self._subs.append(subsidiary)

    def remove(self, name: str) -> bool:
        before = len(self._subs)
        self._subs = [s for s in self._subs if s.name != name]
        return len(self._subs) < before

    def all(self) -> List[Subsidiary]:
        return sorted(self._subs, key=lambda s: s.ownership_pct, reverse=True)

    def wholly_owned(self, threshold: float = 99.0) -> List[Subsidiary]:
        return [s for s in self._subs if s.ownership_pct >= threshold]

    def majority_owned(self) -> List[Subsidiary]:
        return [s for s in self._subs if 50.0 <= s.ownership_pct < 99.0]

    def minority_owned(self) -> List[Subsidiary]:
        return [s for s in self._subs if s.ownership_pct < 50.0]

    def by_country(self) -> Dict[str, List[Subsidiary]]:
        result: Dict[str, List[Subsidiary]] = {}
        for s in self._subs:
            result.setdefault(s.country, []).append(s)
        return result

    def listed(self) -> List[Subsidiary]:
        """Subsidiaries with a ticker (likely listed)."""
        return [s for s in self._subs if s.ticker]

    def total_entities(self) -> int:
        return len(self._subs)

    def countries(self) -> List[str]:
        return sorted({s.country for s in self._subs})

    def find_by_ticker(self, ticker: str) -> Optional[Subsidiary]:
        for s in self._subs:
            if s.ticker and s.ticker.upper() == ticker.upper():
                return s
        return None

    def __len__(self) -> int:
        return len(self._subs)
