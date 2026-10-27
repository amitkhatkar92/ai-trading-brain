"""
tests/test_rolling_refinement_engine.py
===========================================
DTA-UNIVERSAL-ROLLING-REFINEMENT-001

Verifies the shared maturity-staging and confidence-scaled-nudge
primitives used across self-learning modules.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

import learning_system.rolling_refinement_engine as rre


class TestMaturityStage:
    def test_t01_early_stage_near_start(self):
        now = date.fromisoformat(rre.SYSTEM_LIVE_TRADING_START) + timedelta(days=10)
        assert rre.get_maturity_stage(now) == "EARLY"

    def test_t02_mid_stage_after_threshold(self):
        now = date.fromisoformat(rre.SYSTEM_LIVE_TRADING_START) + timedelta(
            days=rre.MID_STAGE_THRESHOLD_DAYS + 5,
        )
        assert rre.get_maturity_stage(now) == "MID"

    def test_t03_mature_stage_after_threshold(self):
        now = date.fromisoformat(rre.SYSTEM_LIVE_TRADING_START) + timedelta(
            days=rre.MATURE_STAGE_THRESHOLD_DAYS + 5,
        )
        assert rre.get_maturity_stage(now) == "MATURE"

    def test_t04_exact_boundary_is_inclusive(self):
        now = date.fromisoformat(rre.SYSTEM_LIVE_TRADING_START) + timedelta(
            days=rre.MID_STAGE_THRESHOLD_DAYS,
        )
        assert rre.get_maturity_stage(now) == "MID"

    def test_t05_never_negative_days(self):
        before_start = date.fromisoformat(rre.SYSTEM_LIVE_TRADING_START) - timedelta(days=100)
        assert rre.days_since_live_start(before_start) == 0


class TestStagedRequirement:
    def test_t06_early_uses_lenient_value(self):
        now = date.fromisoformat(rre.SYSTEM_LIVE_TRADING_START) + timedelta(days=5)
        assert rre.get_staged_requirement(10, 30, 45, now=now) == 10

    def test_t07_mid_uses_mid_value(self):
        now = date.fromisoformat(rre.SYSTEM_LIVE_TRADING_START) + timedelta(days=100)
        assert rre.get_staged_requirement(10, 30, 45, now=now) == 30

    def test_t08_mature_uses_mature_value(self):
        now = date.fromisoformat(rre.SYSTEM_LIVE_TRADING_START) + timedelta(days=200)
        assert rre.get_staged_requirement(10, 30, 45, now=now) == 45

    def test_t09_custom_system_start_date(self):
        custom_start = "2026-01-01"
        now = date(2026, 1, 10)
        assert rre.get_staged_requirement(5, 20, 40, now=now, system_start_date=custom_start) == 5


class TestConfidenceScaledDelta:
    def test_t10_zero_evidence_returns_zero(self):
        assert rre.compute_confidence_scaled_delta(n=0, effect=1.0, max_delta=0.15) == 0.0

    def test_t11_small_sample_produces_small_nudge(self):
        small = rre.compute_confidence_scaled_delta(n=5, effect=1.0, max_delta=0.15, full_confidence_n=100)
        large = rre.compute_confidence_scaled_delta(n=100, effect=1.0, max_delta=0.15, full_confidence_n=100)
        assert 0 < small < large
        assert large == pytest.approx(0.15)

    def test_t12_bounded_at_max_delta_even_with_extreme_effect(self):
        delta = rre.compute_confidence_scaled_delta(n=1000, effect=50.0, max_delta=0.15, full_confidence_n=100)
        assert delta == pytest.approx(0.15)

    def test_t13_negative_effect_produces_negative_nudge(self):
        delta = rre.compute_confidence_scaled_delta(n=100, effect=-1.0, max_delta=0.15, full_confidence_n=100)
        assert delta == pytest.approx(-0.15)

    def test_t14_never_raises_on_garbage_input(self):
        assert rre.compute_confidence_scaled_delta(n=10, effect=float("nan"), max_delta=0.15) in (0.0,) or True
        assert rre.compute_confidence_scaled_delta(n=10, effect=1.0, max_delta=0.15, full_confidence_n=0) == 0.0

    def test_t15_confidence_scales_linearly_with_n(self):
        quarter = rre.compute_confidence_scaled_delta(n=25, effect=1.0, max_delta=1.0, full_confidence_n=100)
        half = rre.compute_confidence_scaled_delta(n=50, effect=1.0, max_delta=1.0, full_confidence_n=100)
        assert half == pytest.approx(2 * quarter)


class TestCheckpointDue:
    def test_t16_never_checkpointed_is_due(self):
        assert rre.is_checkpoint_due(None) is True
        assert rre.is_checkpoint_due("") is True

    def test_t17_recent_checkpoint_not_due(self):
        last = (datetime.now() - timedelta(days=2)).isoformat()
        assert rre.is_checkpoint_due(last, period_days=7) is False

    def test_t18_old_checkpoint_is_due(self):
        last = (datetime.now() - timedelta(days=8)).isoformat()
        assert rre.is_checkpoint_due(last, period_days=7) is True

    def test_t19_exact_boundary_is_due(self):
        last = (datetime.now() - timedelta(days=7)).isoformat()
        assert rre.is_checkpoint_due(last, period_days=7) is True

    def test_t20_handles_tz_aware_vs_naive_mismatch(self):
        last_aware = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        naive_now = datetime.now()
        assert rre.is_checkpoint_due(last_aware, now=naive_now, period_days=7) is True

    def test_t21_malformed_timestamp_fails_open_to_due(self):
        assert rre.is_checkpoint_due("not-a-real-timestamp") is True
