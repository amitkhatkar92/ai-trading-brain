"""tests/unit/investment/company/profile/test_profile_engine.py
Integration tests for CompanyProfileEngine.
"""
from __future__ import annotations

import asyncio
import time
import threading
from typing import List

import pytest

from iios.investment.company.profile.company_profile_engine import CompanyProfileEngine
from iios.investment.company.profile.models import (
    AliasType,
    BusinessProfile,
    BusinessSegment,
    CompanyAlias,
    CompanyClassification,
    CompanyIdentity,
    CompanyMetadata,
    CompanyProfile,
    CompanyRelationships,
    CorporateEvent,
    CorporateEventType,
    GeographicPresence,
    ListingStatus,
    MarketCapCategory,
    OperationsType,
    ProfileEvent,
    ProfileEventType,
    Subsidiary,
    RelationshipType,
    TaxonomyType,
)


class TestCreateProfile:
    def test_creates_profile(self, identity, metadata):
        engine  = CompanyProfileEngine()
        profile = engine.create_profile(identity, metadata)
        assert profile is not None
        assert profile.ticker == "RELIANCE"

    def test_idempotent_create(self, identity, metadata):
        engine = CompanyProfileEngine()
        p1 = engine.create_profile(identity, metadata)
        p2 = engine.create_profile(identity, metadata)
        assert p1.profile_id == p2.profile_id

    def test_profile_count_increments(self, identity, metadata, make_identity, make_metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        engine.create_profile(make_identity("TCS", "TCS Ltd"), make_metadata())
        assert engine.profile_count() == 2

    def test_quality_auto_scored(self, identity, metadata):
        engine  = CompanyProfileEngine()
        profile = engine.create_profile(identity, metadata)
        assert profile.quality is not None
        assert profile.quality.overall >= 0.0

    def test_on_created_callback(self, identity, metadata):
        created = []
        engine  = CompanyProfileEngine()
        engine.on_created = created.append
        engine.create_profile(identity, metadata)
        assert len(created) == 1

    def test_version_starts_at_1(self, identity, metadata):
        engine  = CompanyProfileEngine()
        profile = engine.create_profile(identity, metadata)
        assert profile.version == 1


class TestUpdateMethods:
    def test_update_business(self, identity, metadata):
        engine  = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        bp      = BusinessProfile(
            description="Largest conglomerate",
            business_model="Integrated",
            segments=[BusinessSegment("Oil", "", 60.0, True)],
        )
        profile = engine.update_business("RELIANCE", bp)
        assert profile.business.description == "Largest conglomerate"

    def test_update_classification(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        clf    = CompanyClassification(taxonomy_type=TaxonomyType.GICS, gics_sector="Energy")
        result = engine.update_classification("RELIANCE", clf)
        assert result.classification.gics_sector == "Energy"

    def test_update_geography(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        geo    = [GeographicPresence("IN", "Asia", 80.0, OperationsType.HQ)]
        result = engine.update_geography("RELIANCE", geo)
        assert len(result.geography) == 1

    def test_update_relationships(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        rels   = CompanyRelationships(
            subsidiaries=[Subsidiary("Jio", 85.0, "IN", RelationshipType.SUBSIDIARY)]
        )
        result = engine.update_relationships("RELIANCE", rels)
        assert len(result.relationships.subsidiaries) == 1

    def test_add_alias(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        alias  = CompanyAlias(AliasType.ABBREVIATION, "RIL")
        result = engine.add_alias("RELIANCE", alias)
        assert any(a.value == "RIL" for a in result.aliases)

    def test_add_alias_no_duplicate(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        alias  = CompanyAlias(AliasType.ABBREVIATION, "RIL")
        engine.add_alias("RELIANCE", alias)
        engine.add_alias("RELIANCE", alias)
        profile = engine.get_profile("RELIANCE")
        ril_aliases = [a for a in profile.aliases if a.value == "RIL"]
        assert len(ril_aliases) == 1

    def test_add_corporate_event(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        ev     = CorporateEvent.new(CorporateEventType.IPO, "1977-01-01", "Listed")
        result = engine.add_corporate_event("RELIANCE", ev)
        assert len(result.history) == 1

    def test_mark_delisted(self, identity, metadata):
        engine  = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        profile = engine.mark_delisted("RELIANCE")
        assert profile.identity.listing_status is ListingStatus.DELISTED

    def test_version_increments_on_update(self, identity, metadata):
        engine  = CompanyProfileEngine()
        p       = engine.create_profile(identity, metadata)
        initial = p.version
        engine.update_metadata("RELIANCE", CompanyMetadata(description="Updated"))
        profile = engine.get_profile("RELIANCE")
        assert profile.version == initial + 1

    def test_update_unknown_ticker_returns_none(self, identity, metadata):
        engine = CompanyProfileEngine()
        result = engine.update_business("UNKNOWN_TICKER", BusinessProfile("", ""))
        assert result is None

    def test_on_updated_callback(self, identity, metadata):
        updates = []
        engine  = CompanyProfileEngine()
        engine.on_updated = updates.append
        engine.create_profile(identity, metadata)
        engine.update_metadata("RELIANCE", CompanyMetadata(description="New desc"))
        assert len(updates) >= 1

    def test_callback_exception_does_not_crash(self, identity, metadata):
        def bad(x): raise RuntimeError("intentional")
        engine = CompanyProfileEngine()
        engine.on_created = bad
        engine.create_profile(identity, metadata)   # must not raise


class TestQueryAPIs:
    def test_get_profile(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        p      = engine.get_profile("RELIANCE")
        assert p is not None

    def test_get_profile_unknown(self, identity, metadata):
        engine = CompanyProfileEngine()
        assert engine.get_profile("UNKNOWN") is None

    def test_get_by_isin(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        p      = engine.get_by_isin("INE002A01018")
        assert p is not None

    def test_all_profiles(self, identity, metadata, make_identity, make_metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        engine.create_profile(make_identity("TCS", "TCS Ltd"), make_metadata())
        assert len(engine.all_profiles()) == 2

    def test_active_profiles(self, identity, metadata):
        engine  = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        engine.mark_delisted("RELIANCE")
        active = engine.active_profiles()
        assert len(active) == 0

    def test_search_by_name(self, identity, metadata, make_identity, make_metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        engine.create_profile(make_identity("TCS", "Tata Consultancy Services"),
                              make_metadata())
        results = engine.search(name_query="Reliance")
        assert len(results) == 1

    def test_search_by_sector(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        results = engine.search(sector="Energy")
        assert any(p.ticker == "RELIANCE" for p in results)

    def test_exists(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        assert engine.exists("RELIANCE") is True
        assert engine.exists("UNKNOWN") is False

    def test_quality_refresh(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        score  = engine.quality("RELIANCE", refresh=True)
        assert score is not None

    def test_quality_unknown_ticker(self, identity, metadata):
        engine = CompanyProfileEngine()
        assert engine.quality("UNKNOWN") is None

    def test_version_history_grows(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        engine.update_metadata("RELIANCE", CompanyMetadata(description="v2"))
        engine.update_metadata("RELIANCE", CompanyMetadata(description="v3"))
        history = engine.version_history("RELIANCE")
        assert len(history) >= 3

    def test_recent_events(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        events = engine.recent_events(10)
        assert len(events) >= 1
        assert events[-1].event_type is ProfileEventType.CREATED

    def test_statistics_structure(self, identity, metadata):
        engine = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        stats  = engine.statistics()
        assert "total"      in stats
        assert "active"     in stats
        assert "events_fired" in stats


class TestAsyncCreate:
    def test_async_create_profile(self, identity, metadata):
        engine = CompanyProfileEngine()
        profile = asyncio.run(engine.async_create(identity, metadata))
        assert isinstance(profile, CompanyProfile)
        assert profile.ticker == "RELIANCE"


class TestConcurrency:
    def test_thread_safe_create(self, make_identity, make_metadata):
        engine  = CompanyProfileEngine()
        errors  = []

        def register(i: int) -> None:
            try:
                ident = make_identity(ticker=f"SYM{i:04d}", name=f"Company {i}")
                engine.create_profile(ident, make_metadata())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=register, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        assert engine.profile_count() == 20

    def test_thread_safe_update(self, identity, metadata):
        engine  = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        errors  = []

        def update() -> None:
            try:
                engine.update_metadata(
                    "RELIANCE", CompanyMetadata(description="concurrent update")
                )
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=update) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []


class TestRegistryLookup:
    def test_multi_key_lookup(self, identity, metadata):
        engine  = CompanyProfileEngine()
        engine.create_profile(identity, metadata)
        by_isin  = engine.get_by_isin("INE002A01018")
        by_ticker = engine.get_profile("RELIANCE")
        assert by_isin  is not None
        assert by_ticker is not None
        assert by_isin.profile_id == by_ticker.profile_id
