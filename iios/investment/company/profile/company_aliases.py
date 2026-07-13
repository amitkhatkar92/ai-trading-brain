"""iios/investment/company/profile/company_aliases.py
Manages ticker/name aliases and historical identifiers for a company.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.investment.company.profile.models import AliasType, CompanyAlias


class AliasStore:
    """Manages all aliases for a single company."""

    def __init__(self) -> None:
        self._aliases: List[CompanyAlias] = []

    def add(self, alias: CompanyAlias) -> None:
        # Avoid duplicates by type+value
        if not any(a.alias_type is alias.alias_type and a.value == alias.value
                   for a in self._aliases):
            self._aliases.append(alias)

    def remove(self, alias_type: AliasType, value: str) -> bool:
        before = len(self._aliases)
        self._aliases = [a for a in self._aliases
                         if not (a.alias_type is alias_type and a.value == value)]
        return len(self._aliases) < before

    def by_type(self, alias_type: AliasType) -> List[CompanyAlias]:
        return [a for a in self._aliases if a.alias_type is alias_type]

    def all(self) -> List[CompanyAlias]:
        return list(self._aliases)

    def values(self) -> List[str]:
        return [a.value for a in self._aliases]

    def find(self, value: str) -> Optional[CompanyAlias]:
        for a in self._aliases:
            if a.value == value:
                return a
        return None

    def old_tickers(self) -> List[str]:
        return [a.value for a in self._aliases if a.alias_type is AliasType.TICKER_OLD]

    def trade_names(self) -> List[str]:
        return [a.value for a in self._aliases if a.alias_type is AliasType.TRADE_NAME]

    def __len__(self) -> int:
        return len(self._aliases)


class GlobalAliasIndex:
    """Cross-company alias index: value → profile_id mapping."""

    def __init__(self) -> None:
        self._index: Dict[str, str] = {}   # alias_value → profile_id

    def register(self, profile_id: str, aliases: List[CompanyAlias]) -> None:
        for alias in aliases:
            self._index[alias.value.upper()] = profile_id

    def deregister(self, profile_id: str, aliases: List[CompanyAlias]) -> None:
        for alias in aliases:
            key = alias.value.upper()
            if self._index.get(key) == profile_id:
                del self._index[key]

    def lookup(self, value: str) -> Optional[str]:
        return self._index.get(value.upper())
