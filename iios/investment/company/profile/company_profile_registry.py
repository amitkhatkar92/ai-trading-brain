"""iios/investment/company/profile/company_registry.py
Thread-safe in-memory registry of CompanyProfile objects.
Indexed by profile_id, ticker, ISIN, CUSIP, and LEI for O(1) lookup.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, Set

from iios.investment.company.profile.models import CompanyProfile, ListingStatus


class CompanyProfileRegistry:
    """Stores and retrieves CompanyProfile objects with multi-key indexing.

    Designed to scale to millions of companies: all lookups are O(1)
    dictionary operations.
    """

    def __init__(self) -> None:
        self._lock:     threading.RLock          = threading.RLock()
        self._profiles: Dict[str, CompanyProfile] = {}  # profile_id → profile

        # Secondary indices
        self._by_ticker: Dict[str, str] = {}   # TICKER → profile_id
        self._by_isin:   Dict[str, str] = {}   # ISIN   → profile_id
        self._by_cusip:  Dict[str, str] = {}   # CUSIP  → profile_id
        self._by_lei:    Dict[str, str] = {}   # LEI    → profile_id

    # ── write operations ──────────────────────────────────────────────────────

    def register(self, profile: CompanyProfile) -> None:
        with self._lock:
            pid = profile.profile_id
            self._profiles[pid] = profile
            self._index(profile)

    def update(self, profile: CompanyProfile) -> None:
        with self._lock:
            old = self._profiles.get(profile.profile_id)
            if old:
                self._deindex(old)
            self._profiles[profile.profile_id] = profile
            self._index(profile)

    def deregister(self, profile_id: str) -> bool:
        with self._lock:
            profile = self._profiles.pop(profile_id, None)
            if profile:
                self._deindex(profile)
                return True
            return False

    # ── read operations ───────────────────────────────────────────────────────

    def get(self, profile_id: str) -> Optional[CompanyProfile]:
        with self._lock:
            return self._profiles.get(profile_id)

    def by_ticker(self, ticker: str) -> Optional[CompanyProfile]:
        with self._lock:
            pid = self._by_ticker.get(ticker.upper())
            return self._profiles.get(pid) if pid else None

    def by_isin(self, isin: str) -> Optional[CompanyProfile]:
        with self._lock:
            pid = self._by_isin.get(isin.upper())
            return self._profiles.get(pid) if pid else None

    def by_cusip(self, cusip: str) -> Optional[CompanyProfile]:
        with self._lock:
            pid = self._by_cusip.get(cusip.upper())
            return self._profiles.get(pid) if pid else None

    def by_lei(self, lei: str) -> Optional[CompanyProfile]:
        with self._lock:
            pid = self._by_lei.get(lei.upper())
            return self._profiles.get(pid) if pid else None

    def all(self) -> List[CompanyProfile]:
        with self._lock:
            return list(self._profiles.values())

    def all_active(self) -> List[CompanyProfile]:
        with self._lock:
            return [p for p in self._profiles.values() if p.is_active()]

    def by_sector(self, sector: str) -> List[CompanyProfile]:
        with self._lock:
            return [p for p in self._profiles.values()
                    if p.identity.sector == sector]

    def by_country(self, country: str) -> List[CompanyProfile]:
        with self._lock:
            return [p for p in self._profiles.values()
                    if p.identity.country.upper() == country.upper()]

    def by_exchange(self, exchange: str) -> List[CompanyProfile]:
        with self._lock:
            return [p for p in self._profiles.values()
                    if p.identity.exchange.upper() == exchange.upper()]

    def search_name(self, query: str, limit: int = 20) -> List[CompanyProfile]:
        """Case-insensitive substring search on company name."""
        q = query.lower()
        with self._lock:
            results = [
                p for p in self._profiles.values()
                if q in p.identity.name.lower()
            ]
        return results[:limit]

    def count(self) -> int:
        with self._lock:
            return len(self._profiles)

    def tickers(self) -> List[str]:
        with self._lock:
            return sorted(self._by_ticker.keys())

    def exists(self, profile_id: str) -> bool:
        with self._lock:
            return profile_id in self._profiles

    def ticker_exists(self, ticker: str) -> bool:
        with self._lock:
            return ticker.upper() in self._by_ticker

    # ── indexing ──────────────────────────────────────────────────────────────

    def _index(self, profile: CompanyProfile) -> None:
        pid = profile.profile_id
        self._by_ticker[profile.identity.ticker.upper()] = pid
        if profile.identity.isin:
            self._by_isin[profile.identity.isin.upper()] = pid
        if profile.identity.cusip:
            self._by_cusip[profile.identity.cusip.upper()] = pid
        if profile.identity.lei:
            self._by_lei[profile.identity.lei.upper()] = pid

    def _deindex(self, profile: CompanyProfile) -> None:
        self._by_ticker.pop(profile.identity.ticker.upper(), None)
        if profile.identity.isin:
            self._by_isin.pop(profile.identity.isin.upper(), None)
        if profile.identity.cusip:
            self._by_cusip.pop(profile.identity.cusip.upper(), None)
        if profile.identity.lei:
            self._by_lei.pop(profile.identity.lei.upper(), None)
