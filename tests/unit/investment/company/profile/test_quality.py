"""tests/unit/investment/company/profile/test_quality.py"""
from __future__ import annotations

import time

import pytest

from iios.investment.company.profile.models import CompanyProfile, CompanyIdentity, CompanyMetadata
from iios.investment.company.profile.profile_confidence import (
    compute_confidence,
    compute_completeness,
    is_reliable,
)
from iios.investment.company.profile.profile_quality import ProfileQualityEngine
from iios.investment.company.profile.profile_statistics import (
    avg_completeness,
    avg_freshness,
    avg_overall,
    below_threshold,
    country_distribution,
    listing_status_distribution,
    most_common_missing,
    profiles_with_business,
    profiles_with_classification,
    sector_distribution,
)


class TestProfileQualityEngine:
    def test_score_minimal_profile(self):
        ts      = time.time()
        ident   = CompanyIdentity(ticker="TCS", name="TCS", exchange="NSE",
                                   country="IN", currency="INR")
        meta    = CompanyMetadata()
        profile = CompanyProfile.new(ident, meta, ts)
        engine  = ProfileQualityEngine()
        score   = engine.score(profile, ts)
        assert 0.0 <= score.completeness <= 100.0
        assert 0.0 <= score.overall     <= 100.0

    def test_full_profile_higher_score(self, full_profile):
        ts     = time.time()
        engine = ProfileQualityEngine()
        score  = engine.score(full_profile, ts)
        # Full profile should have decent completeness
        assert score.completeness > 50.0

    def test_full_profile_high_coverage(self, full_profile):
        ts     = time.time()
        engine = ProfileQualityEngine()
        score  = engine.score(full_profile, ts)
        assert score.coverage >= 75.0

    def test_missing_fields_populated(self):
        ts      = time.time()
        ident   = CompanyIdentity(ticker="X", name="X", exchange="NSE",
                                   country="IN", currency="INR")
        meta    = CompanyMetadata()
        profile = CompanyProfile.new(ident, meta, ts)
        engine  = ProfileQualityEngine()
        score   = engine.score(profile, ts)
        # Should have missing fields for business, classification, etc.
        assert len(score.missing_fields) > 0

    def test_freshness_decays_with_age(self, full_profile):
        engine    = ProfileQualityEngine()
        fresh_ts  = time.time()
        stale_ts  = fresh_ts + 100 * 86400   # 100 days in the future
        score_now  = engine.score(full_profile, fresh_ts)
        score_old  = engine.score(full_profile, stale_ts)
        assert score_now.freshness > score_old.freshness

    def test_confidence_bonus_for_isin(self, full_profile):
        engine = ProfileQualityEngine()
        ts     = time.time()
        score_with_isin = engine.score(full_profile, ts)
        import copy
        no_isin_profile = copy.deepcopy(full_profile)
        no_isin_profile.identity.isin = None
        score_without   = engine.score(no_isin_profile, ts)
        assert score_with_isin.confidence >= score_without.confidence

    def test_overall_in_range(self, full_profile):
        engine = ProfileQualityEngine()
        score  = engine.score(full_profile)
        assert 0.0 <= score.overall <= 100.0


class TestProfileConfidence:
    def test_compute_confidence_full_profile(self, full_profile):
        conf = compute_confidence(full_profile)
        assert 0.0 <= conf <= 100.0

    def test_full_profile_higher_confidence_than_minimal(self, full_profile):
        ts      = time.time()
        ident   = CompanyIdentity(ticker="MIN", name="Minimal", exchange="NSE",
                                   country="IN", currency="INR")
        meta    = CompanyMetadata()
        minimal = CompanyProfile.new(ident, meta, ts)
        assert compute_confidence(full_profile) > compute_confidence(minimal)

    def test_compute_completeness(self, full_profile):
        comp = compute_completeness(full_profile)
        assert 0.0 <= comp <= 100.0

    def test_is_reliable_full(self, full_profile):
        assert is_reliable(full_profile, threshold=10.0) is True

    def test_is_reliable_minimal(self):
        ts      = time.time()
        ident   = CompanyIdentity(ticker="X", name="X", exchange="NSE",
                                   country="IN", currency="INR")
        meta    = CompanyMetadata()
        minimal = CompanyProfile.new(ident, meta, ts)
        # Minimal profile should not be reliable at 90% threshold
        assert is_reliable(minimal, threshold=90.0) is False


class TestProfileStatistics:
    def test_avg_overall(self, full_profile, make_profile):
        engine = ProfileQualityEngine()
        ts     = time.time()
        scores = [engine.score(make_profile(t), ts)
                  for t in ("RELIANCE", "TCS", "INFOSYS")]
        avg    = avg_overall(scores)
        assert 0.0 <= avg <= 100.0

    def test_avg_completeness_nonempty(self, full_profile, make_profile):
        engine = ProfileQualityEngine()
        ts     = time.time()
        scores = [engine.score(make_profile(t), ts) for t in ("A", "B")]
        assert 0.0 <= avg_completeness(scores) <= 100.0

    def test_avg_freshness(self, full_profile, make_profile):
        engine = ProfileQualityEngine()
        ts     = time.time()
        scores = [engine.score(make_profile(t), ts) for t in ("A", "B")]
        assert 0.0 <= avg_freshness(scores) <= 100.0

    def test_below_threshold(self, full_profile, make_profile):
        engine = ProfileQualityEngine()
        ts     = time.time()
        scores = [engine.score(make_profile(t), ts) for t in ("A", "B", "C")]
        count  = below_threshold(scores, threshold=0.0)
        assert count == 0   # all above 0

    def test_most_common_missing(self):
        from iios.investment.company.profile.models import ProfileQualityScore
        scores = [
            ProfileQualityScore("p1", 50.0, 50.0, 50.0, 50.0, 50.0,
                                missing_fields=["business", "classification"]),
            ProfileQualityScore("p2", 40.0, 50.0, 40.0, 40.0, 42.0,
                                missing_fields=["business", "geography"]),
        ]
        common = most_common_missing(scores, top_n=3)
        assert "business" in common

    def test_sector_distribution(self, make_profile):
        profiles = [make_profile(t) for t in ("A", "B", "C")]
        dist     = sector_distribution(profiles)
        assert isinstance(dist, dict)
        assert sum(dist.values()) == 3

    def test_country_distribution(self, make_profile):
        profiles = [make_profile(t) for t in ("A", "B")]
        dist     = country_distribution(profiles)
        assert "IN" in dist

    def test_profiles_with_business(self, full_profile):
        profiles = [full_profile]
        result   = profiles_with_business(profiles)
        assert len(result) == 1

    def test_profiles_with_classification(self, full_profile):
        profiles = [full_profile]
        result   = profiles_with_classification(profiles)
        assert len(result) == 1
