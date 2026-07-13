"""iios/investment/company/profile/company_profile_engine.py
Institutional Company Profile Intelligence Engine — primary entry point.

  engine = CompanyProfileEngine()
  profile = engine.create_profile(identity, metadata)
  engine.update_business(ticker, business_profile)
  engine.update_classification(ticker, classification)
  snap = engine.get_profile(ticker)
"""
from __future__ import annotations

import asyncio
import logging
import time
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Deque, Dict, List, Optional

from iios.investment.company.profile.classification_engine import ClassificationEngine
from iios.investment.company.profile.company_profile_registry import CompanyProfileRegistry
from iios.investment.company.profile.models import (
    BusinessProfile,
    CompanyAlias,
    CompanyClassification,
    CompanyIdentity,
    CompanyMetadata,
    CompanyProfile,
    CompanyRelationships,
    CorporateEvent,
    GeographicPresence,
    ListingStatus,
    ProfileEvent,
    ProfileEventType,
    ProfileQualityScore,
)
from iios.investment.company.profile.profile_quality import ProfileQualityEngine

log = logging.getLogger(__name__)


class CompanyProfileEngine:
    """Authoritative identity and business knowledge source for every company.

    Responsibilities:
    - Manage company profiles (create, update, version, query)
    - Track profile evolution with full historical lineage
    - Compute and cache profile quality scores
    - Publish profile events to registered callbacks
    - Provide high-performance, multi-key lookup APIs

    This engine NEVER performs financial analysis, valuation, earnings
    analysis, growth scoring, governance scoring, or investment ranking.
    Those are the responsibility of downstream engines.
    """

    def __init__(
        self,
        quality_auto_score: bool = True,
        event_history_len:  int  = 500,
    ) -> None:
        self._lock               = threading.RLock()
        self._registry           = CompanyProfileRegistry()
        self._quality_engine     = ProfileQualityEngine()
        self._classification_eng = ClassificationEngine()
        self._quality_auto_score = quality_auto_score
        self._event_history: Deque[ProfileEvent] = deque(maxlen=event_history_len)

        # Version history: profile_id → list of (version, profile_snapshot_dict)
        self._version_history: Dict[str, List[dict]] = {}

        # Callbacks
        self.on_created: Optional[Callable[[CompanyProfile], None]] = None
        self.on_updated: Optional[Callable[[CompanyProfile], None]] = None
        self.on_event:   Optional[Callable[[ProfileEvent],   None]] = None

        self._executor: Optional[ThreadPoolExecutor] = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def create_profile(
        self,
        identity: CompanyIdentity,
        metadata: CompanyMetadata,
        ts:       Optional[float] = None,
    ) -> CompanyProfile:
        ts = ts or time.time()
        with self._lock:
            existing = self._registry.by_ticker(identity.ticker)
            if existing:
                return existing
            profile = CompanyProfile.new(identity, metadata, ts)
            if self._quality_auto_score:
                profile.quality = self._quality_engine.score(profile, ts)
            self._registry.register(profile)
            self._save_version(profile)
            event = ProfileEvent.new(
                profile.profile_id, ProfileEventType.CREATED,
                profile.ticker, ts,
            )
            self._publish_event(event)
            if self.on_created:
                try:
                    self.on_created(profile)
                except Exception:
                    log.exception("on_created callback error")
            return profile

    # ── update methods ────────────────────────────────────────────────────────

    def update_identity(
        self,
        ticker:   str,
        identity: CompanyIdentity,
        ts:       Optional[float] = None,
    ) -> Optional[CompanyProfile]:
        return self._mutate(ticker, ts, lambda p: self._apply_identity(p, identity),
                            ProfileEventType.IDENTITY_CHANGED)

    def update_metadata(
        self,
        ticker:   str,
        metadata: CompanyMetadata,
        ts:       Optional[float] = None,
    ) -> Optional[CompanyProfile]:
        return self._mutate(ticker, ts, lambda p: setattr(p, "metadata", metadata),
                            ProfileEventType.UPDATED)

    def update_business(
        self,
        ticker:  str,
        business: BusinessProfile,
        ts:      Optional[float] = None,
    ) -> Optional[CompanyProfile]:
        return self._mutate(ticker, ts, lambda p: setattr(p, "business", business),
                            ProfileEventType.UPDATED)

    def update_geography(
        self,
        ticker:    str,
        geography: List[GeographicPresence],
        ts:        Optional[float] = None,
    ) -> Optional[CompanyProfile]:
        return self._mutate(ticker, ts, lambda p: setattr(p, "geography", list(geography)),
                            ProfileEventType.UPDATED)

    def update_classification(
        self,
        ticker:         str,
        classification: CompanyClassification,
        ts:             Optional[float] = None,
    ) -> Optional[CompanyProfile]:
        return self._mutate(ticker, ts,
                            lambda p: setattr(p, "classification", classification),
                            ProfileEventType.CLASSIFICATION_CHANGED)

    def update_relationships(
        self,
        ticker:        str,
        relationships: CompanyRelationships,
        ts:            Optional[float] = None,
    ) -> Optional[CompanyProfile]:
        return self._mutate(ticker, ts,
                            lambda p: setattr(p, "relationships", relationships),
                            ProfileEventType.RELATIONSHIP_CHANGED)

    def add_alias(
        self,
        ticker: str,
        alias:  CompanyAlias,
        ts:     Optional[float] = None,
    ) -> Optional[CompanyProfile]:
        def _add(p: CompanyProfile) -> None:
            if not any(a.alias_type is alias.alias_type and a.value == alias.value
                       for a in p.aliases):
                p.aliases.append(alias)
        return self._mutate(ticker, ts, _add, ProfileEventType.UPDATED)

    def add_corporate_event(
        self,
        ticker: str,
        event:  CorporateEvent,
        ts:     Optional[float] = None,
    ) -> Optional[CompanyProfile]:
        def _add(p: CompanyProfile) -> None:
            if not any(e.event_id == event.event_id for e in p.history):
                p.history.append(event)
                p.history.sort(key=lambda e: e.date)
        return self._mutate(ticker, ts, _add, ProfileEventType.HISTORY_APPENDED)

    def mark_delisted(self, ticker: str, ts: Optional[float] = None) -> Optional[CompanyProfile]:
        def _delist(p: CompanyProfile) -> None:
            p.identity.listing_status = ListingStatus.DELISTED
        return self._mutate(ticker, ts, _delist, ProfileEventType.DELISTED)

    # ── query APIs ────────────────────────────────────────────────────────────

    def get_profile(self, ticker: str) -> Optional[CompanyProfile]:
        return self._registry.by_ticker(ticker)

    def get_by_isin(self, isin: str) -> Optional[CompanyProfile]:
        return self._registry.by_isin(isin)

    def get_by_lei(self, lei: str) -> Optional[CompanyProfile]:
        return self._registry.by_lei(lei)

    def get_by_cusip(self, cusip: str) -> Optional[CompanyProfile]:
        return self._registry.by_cusip(cusip)

    def all_profiles(self) -> List[CompanyProfile]:
        return self._registry.all()

    def active_profiles(self) -> List[CompanyProfile]:
        return self._registry.all_active()

    def search(
        self,
        *,
        name_query:    Optional[str]  = None,
        sector:        Optional[str]  = None,
        country:       Optional[str]  = None,
        exchange:      Optional[str]  = None,
        limit:         int            = 20,
    ) -> List[CompanyProfile]:
        with self._lock:
            if name_query:
                results = self._registry.search_name(name_query, limit)
            elif sector:
                results = self._registry.by_sector(sector)
            elif country:
                results = self._registry.by_country(country)
            elif exchange:
                results = self._registry.by_exchange(exchange)
            else:
                results = self._registry.all()
            return results[:limit]

    def exists(self, ticker: str) -> bool:
        return self._registry.ticker_exists(ticker)

    def profile_count(self) -> int:
        return self._registry.count()

    def quality(self, ticker: str, refresh: bool = False) -> Optional[ProfileQualityScore]:
        profile = self._registry.by_ticker(ticker)
        if not profile:
            return None
        if refresh or profile.quality is None:
            with self._lock:
                profile.quality = self._quality_engine.score(profile)
                self._registry.update(profile)
        return profile.quality

    def recent_events(self, n: int = 20) -> List[ProfileEvent]:
        return list(self._event_history)[-n:]

    def version_history(self, ticker: str) -> List[dict]:
        profile = self._registry.by_ticker(ticker)
        if not profile:
            return []
        return list(self._version_history.get(profile.profile_id, []))

    def statistics(self) -> dict:
        all_p = self._registry.all()
        return {
            "total":        len(all_p),
            "active":       len([p for p in all_p if p.is_active()]),
            "with_business": len([p for p in all_p if p.business]),
            "with_classification": len([p for p in all_p if p.classification]),
            "with_relationships": len([p for p in all_p if p.relationships]),
            "events_fired": len(self._event_history),
        }

    # ── async update ──────────────────────────────────────────────────────────

    async def async_create(
        self,
        identity: CompanyIdentity,
        metadata: CompanyMetadata,
    ) -> CompanyProfile:
        loop = asyncio.get_event_loop()
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1)
        return await loop.run_in_executor(
            self._executor,
            lambda: self.create_profile(identity, metadata),
        )

    # ── internals ─────────────────────────────────────────────────────────────

    def _mutate(
        self,
        ticker:     str,
        ts:         Optional[float],
        mutation:   Callable[[CompanyProfile], None],
        event_type: ProfileEventType,
    ) -> Optional[CompanyProfile]:
        ts = ts or time.time()
        with self._lock:
            profile = self._registry.by_ticker(ticker)
            if not profile:
                log.warning("profile not found for ticker %s", ticker)
                return None
            mutation(profile)
            profile.version   += 1
            profile.updated_at = ts
            if self._quality_auto_score:
                profile.quality = self._quality_engine.score(profile, ts)
            self._registry.update(profile)
            self._save_version(profile)
            ev = ProfileEvent.new(profile.profile_id, event_type, ticker, ts)
            self._publish_event(ev)
            if self.on_updated:
                try:
                    self.on_updated(profile)
                except Exception:
                    log.exception("on_updated callback error")
            return profile

    @staticmethod
    def _apply_identity(p: CompanyProfile, new: CompanyIdentity) -> None:
        p.identity = new

    def _save_version(self, profile: CompanyProfile) -> None:
        pid  = profile.profile_id
        hist = self._version_history.setdefault(pid, [])
        hist.append({
            "version":    profile.version,
            "updated_at": profile.updated_at,
            "ticker":     profile.ticker,
            "name":       profile.name,
        })

    def _publish_event(self, event: ProfileEvent) -> None:
        self._event_history.append(event)
        if self.on_event:
            try:
                self.on_event(event)
            except Exception:
                log.exception("on_event callback error")
