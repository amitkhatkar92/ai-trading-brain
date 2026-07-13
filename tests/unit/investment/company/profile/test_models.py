"""tests/unit/investment/company/profile/test_models.py"""
from __future__ import annotations

import json
import time

import pytest

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
    Product,
    ProfileEvent,
    ProfileEventType,
    ProfileQualityScore,
    RelatedEntity,
    RelationshipType,
    Service,
    Subsidiary,
    TaxonomyType,
)


class TestCompanyIdentity:
    def test_defaults(self):
        ident = CompanyIdentity(ticker="TCS", name="TCS", exchange="NSE",
                                country="IN", currency="INR")
        assert ident.listing_status is ListingStatus.LISTED
        assert ident.isin is None

    def test_to_dict_keys(self, identity):
        d = identity.to_dict()
        assert "ticker" in d and "name" in d and "isin" in d
        assert d["ticker"] == "RELIANCE"

    def test_serialisable(self, identity):
        json.dumps(identity.to_dict())


class TestCompanyMetadata:
    def test_to_dict(self, metadata):
        d = metadata.to_dict()
        assert d["founding_year"] == 1973
        assert d["market_cap_category"] == "mega"

    def test_serialisable(self, metadata):
        json.dumps(metadata.to_dict())


class TestBusinessSegment:
    def test_to_dict(self):
        seg = BusinessSegment("Chemicals", "Chemical segment", 40.0, True)
        d   = seg.to_dict()
        assert d["revenue_pct"] == pytest.approx(40.0)
        assert d["is_primary"] is True


class TestBusinessProfile:
    def test_primary_segment_explicit(self):
        bp = BusinessProfile(
            description="Test", business_model="B2B",
            segments=[
                BusinessSegment("A", "", 30.0, False),
                BusinessSegment("B", "", 60.0, True),
            ],
        )
        assert bp.primary_segment().name == "B"

    def test_primary_segment_implicit(self):
        bp = BusinessProfile(
            description="Test", business_model="B2C",
            segments=[
                BusinessSegment("Small", "", 20.0, False),
                BusinessSegment("Big",   "", 80.0, False),
            ],
        )
        assert bp.primary_segment().name == "Big"

    def test_primary_segment_empty(self):
        bp = BusinessProfile(description="", business_model="")
        assert bp.primary_segment() is None

    def test_to_dict_serialisable(self, full_profile):
        json.dumps(full_profile.business.to_dict())


class TestGeographicPresence:
    def test_to_dict(self):
        gp = GeographicPresence("IN", "Asia", 70.0, OperationsType.HQ)
        d  = gp.to_dict()
        assert d["operations_type"] == "hq"
        assert d["revenue_pct"] == pytest.approx(70.0)


class TestCorporateEvent:
    def test_new_factory(self):
        ev = CorporateEvent.new(CorporateEventType.IPO, "2010-11-18", "Listed on NSE")
        assert len(ev.event_id) == 36
        assert ev.event_type is CorporateEventType.IPO

    def test_to_dict_serialisable(self):
        ev = CorporateEvent.new(CorporateEventType.MERGER, "2020-06-01", "Merger with XYZ",
                                {"acquiree": "XYZ Corp"})
        json.dumps(ev.to_dict())


class TestSubsidiary:
    def test_to_dict(self):
        sub = Subsidiary("Jio", 85.0, "IN", RelationshipType.SUBSIDIARY, "JIOLT")
        d   = sub.to_dict()
        assert d["ownership_pct"] == pytest.approx(85.0)
        assert d["ticker"] == "JIOLT"


class TestRelatedEntity:
    def test_new_factory(self):
        ent = RelatedEntity.new("Network18", RelationshipType.ASSOCIATE,
                                ownership_pct=70.0, ticker="NETWORK18")
        assert len(ent.entity_id) == 36
        assert ent.relationship_type is RelationshipType.ASSOCIATE


class TestCompanyClassification:
    def test_to_dict(self, full_profile):
        d = full_profile.classification.to_dict()
        assert d["taxonomy_type"] == "gics"
        assert isinstance(d["investment_themes"], list)

    def test_serialisable(self, full_profile):
        json.dumps(full_profile.classification.to_dict())


class TestCompanyRelationships:
    def test_all_related(self, full_profile):
        rel    = full_profile.relationships
        result = rel.all_related()
        assert len(result) >= 2   # 2 subsidiaries + 1 associate

    def test_to_dict_serialisable(self, full_profile):
        json.dumps(full_profile.relationships.to_dict())


class TestProfileQualityScore:
    def test_to_dict(self):
        q = ProfileQualityScore("pid", 80.0, 90.0, 75.0, 85.0, 82.0, ["metadata.ipo_date"])
        d = q.to_dict()
        assert d["overall"] == pytest.approx(82.0)
        assert "metadata.ipo_date" in d["missing_fields"]

    def test_serialisable(self):
        q = ProfileQualityScore("pid", 70.0, 60.0, 65.0, 75.0, 67.0)
        json.dumps(q.to_dict())


class TestCompanyProfile:
    def test_new_factory(self, identity, metadata):
        ts      = time.time()
        profile = CompanyProfile.new(identity, metadata, ts)
        assert profile.version == 1
        assert profile.ticker == "RELIANCE"
        assert len(profile.profile_id) == 36

    def test_is_active(self, full_profile):
        assert full_profile.is_active() is True
        full_profile.identity.listing_status = ListingStatus.DELISTED
        assert full_profile.is_active() is False

    def test_to_dict_serialisable(self, full_profile):
        json.dumps(full_profile.to_dict())

    def test_to_dict_keys(self, full_profile):
        d = full_profile.to_dict()
        for key in ("profile_id", "version", "identity", "metadata",
                    "business", "geography", "classification",
                    "relationships", "history", "aliases"):
            assert key in d


class TestProfileEvent:
    def test_new_factory(self, full_profile):
        ev = ProfileEvent.new(full_profile.profile_id, ProfileEventType.CREATED,
                              full_profile.ticker, time.time())
        assert len(ev.event_id) == 36
        assert ev.event_type is ProfileEventType.CREATED

    def test_serialisable(self, full_profile):
        ev = ProfileEvent.new("pid", ProfileEventType.UPDATED, "TCS", time.time())
        json.dumps(ev.to_dict())
