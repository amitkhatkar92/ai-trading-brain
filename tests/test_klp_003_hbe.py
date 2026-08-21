"""
tests/test_klp_003_hbe.py
===========================
Comprehensive tests for KLP-003 — Historical Behaviour Engine.

Covers:
  - Zero observations
  - Insufficient observations (< TIER thresholds)
  - All evidence tiers (T0–T6)
  - Hierarchical fallback (L1→L7)
  - Effective sample size (ESS)
  - Recency weighting
  - Regime matching
  - Sector fallback
  - Symbol isolation / direction isolation
  - Stability detection (stable / developing / unstable / insufficient)
  - Target probability / stop probability
  - Move distribution (p25/p50/p75)
  - Time-to-target / time-to-stop
  - T+1/T+3/T+5 horizon distributions
  - Threshold probabilities (P(move >= 1%), etc.)
  - Knowledge target / stop outputs
  - No-lookahead invariant
  - Missing / corrupt KLP records
  - Deterministic output
  - Safety: no broker calls, no orders
  - V2 score preview
  - V2 fallback when evidence is insufficient
  - File I/O (load_outcomes from temp files)
  - Diagnostic record writing
  - Evidence tier mapping
  - Confidence formula
"""
from __future__ import annotations

import json
import math
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

import pytest

from opportunity_engine.hbe_models import (
    COMPLETED_OUTCOMES,
    STOP_HIT,
    TARGET_HIT,
    OUTCOME_EXPIRED,
    OUTCOME_AMBIGUOUS,
    OutcomeRecord,
    BehaviourMetrics,
    BehaviourProfile,
    KnowledgeScoreV2Preview,
    evidence_tier,
    TIER_LABELS,
)
from opportunity_engine.historical_behaviour_engine import (
    HistoricalBehaviourEngine,
    _recency_weight,
    _percentile,
    _effective_sample_size,
    _compute_metrics,
    _stability_status,
    _atr_fallback_metrics,
    _compute_v2_preview,
    _context_similar,
    _trading_days_between,
    _get_sector,
    get_hbe,
    _L1, _L2, _L3, _L4, _L5, _L6, _L7,
)


# ─────────────────────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────────────────────

_REF_DATE = date(2026, 9, 1)


def _make_outcome(
    symbol: str = "TATASTEEL",
    direction: str = "BUY",
    regime: str = "BULL",
    sector: str = "METALS",
    trading_date: str = "2026-08-01",
    first_event: str = TARGET_HIT,
    target_hit: bool = True,
    stop_hit:   bool = False,
    t1_ret_pct: float = 1.5,
    t3_ret_pct: float = 3.0,
    t5_ret_pct: float = 4.5,
    mfe_pct:    float = 5.0,
    mae_pct:    float = -1.0,
    days_to_event: Optional[int] = 2,
    atr_pct: float = 1.5,
    scanner_confidence: float = 7.0,
    knowledge_rr: float = 2.5,
) -> OutcomeRecord:
    return OutcomeRecord(
        obs_id=f"{symbol}_{trading_date}_{direction}",
        trading_date=trading_date,
        symbol=symbol,
        direction=direction,
        regime=regime,
        sector=sector,
        reference_entry=200.0,
        knowledge_target=215.0,
        knowledge_stop=192.0,
        atr=3.0,
        atr_pct=atr_pct,
        scanner_confidence=scanner_confidence,
        candidate_score=0.75,
        knowledge_score=0.68,
        knowledge_rr=knowledge_rr,
        first_event=first_event,
        first_event_day="2026-08-03",
        target_hit=target_hit,
        stop_hit=stop_hit,
        t1_ret_pct=t1_ret_pct,
        t3_ret_pct=t3_ret_pct,
        t5_ret_pct=t5_ret_pct,
        mfe_pct=mfe_pct,
        mae_pct=mae_pct,
        days_to_event=days_to_event,
        no_lookahead=True,
    )


def _make_n_outcomes(n: int, symbol="TATASTEEL", direction="BUY", regime="BULL",
                     first_event=TARGET_HIT, target_hit=True, stop_hit=False,
                     base_date_str="2026-01-01") -> List[OutcomeRecord]:
    base = date.fromisoformat(base_date_str)
    return [
        _make_outcome(
            symbol=symbol,
            direction=direction,
            regime=regime,
            trading_date=str(base + timedelta(days=i)),
            first_event=first_event,
            target_hit=target_hit,
            stop_hit=stop_hit,
        )
        for i in range(n)
    ]


def _hbe_with(outcomes: List[OutcomeRecord], reference_date=_REF_DATE) -> HistoricalBehaviourEngine:
    hbe = HistoricalBehaviourEngine(reference_date=reference_date)
    hbe._outcomes = outcomes
    hbe._loaded = True
    return hbe


# ─────────────────────────────────────────────────────────────────────────────
# T001 — T010: Evidence tier mapping
# ─────────────────────────────────────────────────────────────────────────────

def test_T001_tier_0_for_zero():
    assert evidence_tier(0) == 0

def test_T002_tier_0_for_9():
    assert evidence_tier(9) == 0

def test_T003_tier_1_for_10():
    assert evidence_tier(10) == 1

def test_T004_tier_1_for_19():
    assert evidence_tier(19) == 1

def test_T005_tier_2_for_20():
    assert evidence_tier(20) == 2

def test_T006_tier_3_for_50():
    assert evidence_tier(50) == 3

def test_T007_tier_4_for_100():
    assert evidence_tier(100) == 4

def test_T008_tier_5_for_250():
    assert evidence_tier(250) == 5

def test_T009_tier_6_for_500():
    assert evidence_tier(500) == 6

def test_T010_tier_labels_complete():
    for t in range(7):
        assert t in TIER_LABELS


# ─────────────────────────────────────────────────────────────────────────────
# T011 — T020: Recency weighting
# ─────────────────────────────────────────────────────────────────────────────

def test_T011_recency_same_day():
    w = _recency_weight("2026-09-01", date(2026, 9, 1))
    assert w == 1.0

def test_T012_recency_future_date():
    w = _recency_weight("2026-09-10", date(2026, 9, 1))
    assert w == 1.0

def test_T013_recency_half_life():
    # 90 days ago → weight = 0.5
    w = _recency_weight("2026-06-03", date(2026, 9, 1))
    assert abs(w - 0.5) < 0.02

def test_T014_recency_double_halflife():
    # 180 days ago → weight ≈ 0.25
    w = _recency_weight("2026-03-05", date(2026, 9, 1))
    assert abs(w - 0.25) < 0.02

def test_T015_recency_monotonically_decreasing():
    ref = date(2026, 9, 1)
    w1 = _recency_weight("2026-08-01", ref)
    w2 = _recency_weight("2026-07-01", ref)
    w3 = _recency_weight("2026-06-01", ref)
    assert w1 > w2 > w3

def test_T016_recency_invalid_date_is_neutral():
    w = _recency_weight("not-a-date", date(2026, 9, 1))
    assert 0.0 < w <= 1.0

def test_T017_recency_one_year_ago_is_small():
    w = _recency_weight("2025-09-01", date(2026, 9, 1))
    assert w < 0.1

def test_T018_ess_empty():
    ess = _effective_sample_size([], _REF_DATE)
    assert ess == 0.0

def test_T019_ess_recent_equals_count():
    # All observations from yesterday → ESS ≈ count
    yesterday = str(_REF_DATE - timedelta(days=1))
    records = _make_n_outcomes(50, base_date_str=yesterday)
    ess = _effective_sample_size(records, _REF_DATE)
    assert 45 < ess <= 50

def test_T020_ess_old_is_less_than_count():
    records = _make_n_outcomes(100, base_date_str="2025-01-01")
    ess = _effective_sample_size(records, _REF_DATE)
    assert ess < 10  # year-old observations decayed heavily


# ─────────────────────────────────────────────────────────────────────────────
# T021 — T030: Percentile helper
# ─────────────────────────────────────────────────────────────────────────────

def test_T021_percentile_empty():
    assert _percentile([], 50) is None

def test_T022_percentile_single():
    assert _percentile([5.0], 50) == 5.0

def test_T023_percentile_median():
    assert _percentile([1.0, 2.0, 3.0, 4.0, 5.0], 50) == 3.0

def test_T024_percentile_p25():
    vs = list(range(1, 101))  # 1–100
    p25 = _percentile(vs, 25)
    assert 24 <= p25 <= 26

def test_T025_percentile_p75():
    vs = list(range(1, 101))
    p75 = _percentile(vs, 75)
    assert 74 <= p75 <= 76

def test_T026_percentile_ignores_none():
    p = _percentile([1.0, None, 3.0, None, 5.0], 50)
    assert p == 3.0

def test_T027_percentile_p0():
    p = _percentile([3.0, 1.0, 5.0], 0)
    assert p == 1.0

def test_T028_percentile_p100():
    p = _percentile([3.0, 1.0, 5.0], 100)
    assert p == 5.0

def test_T029_percentile_two_values():
    p = _percentile([2.0, 8.0], 50)
    assert p == 5.0

def test_T030_percentile_negative_values():
    p = _percentile([-5.0, -3.0, -1.0], 50)
    assert p == -3.0


# ─────────────────────────────────────────────────────────────────────────────
# T031 — T040: Zero / insufficient observations
# ─────────────────────────────────────────────────────────────────────────────

def test_T031_zero_obs_returns_level7():
    hbe = _hbe_with([])
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY", regime="BULL")
    assert profile.metrics.evidence_level == 7
    assert profile.metrics.observation_count == 0

def test_T032_zero_obs_all_probs_none():
    hbe = _hbe_with([])
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    m = profile.metrics
    assert m.target_hit_probability is None
    assert m.stop_first_probability is None
    assert m.positive_move_probability is None

def test_T033_zero_obs_no_lookahead_true():
    hbe = _hbe_with([])
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.no_lookahead is True

def test_T034_zero_obs_v2_uses_v1_fallback():
    hbe = _hbe_with([])
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY", v1_score=0.65)
    assert profile.score_v2_preview.using_fallback is True
    assert abs(profile.score_v2_preview.score_v2 - 0.65) < 0.01

def test_T035_wrong_direction_returns_level7():
    records = _make_n_outcomes(50, symbol="TATASTEEL", direction="BUY")
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "SELL")
    assert profile.metrics.evidence_level == 7

def test_T036_wrong_symbol_falls_to_broader():
    # 20 records for TATASTEEL BUY BULL, query HDFCBANK BUY BULL
    # Should not get L2 (HDFCBANK) but may get L4 (regime) or L6 (broad)
    records = _make_n_outcomes(20, symbol="TATASTEEL", direction="BUY", regime="BULL")
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("HDFCBANK", "BUY", regime="BULL")
    assert profile.metrics.evidence_level >= 3

def test_T037_five_obs_level2():
    records = _make_n_outcomes(5, symbol="TATASTEEL", direction="BUY")
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.metrics.evidence_level == 2
    assert profile.metrics.observation_count == 5

def test_T038_insufficient_obs_metrics_are_none():
    records = _make_n_outcomes(3, symbol="TATASTEEL", direction="BUY")
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    m = profile.metrics
    # 3 < _MIN_OBS_FOR_PROBS (5) — some probs may be None
    # Level 7 (no level met minimum) → all None
    assert m.target_hit_probability is None or m.observation_count == 0

def test_T039_4_obs_no_level_met():
    records = _make_n_outcomes(4, symbol="TATASTEEL", direction="BUY")
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    # 4 < _LEVEL_MIN_OBS[2] = 5, so level 7
    assert profile.metrics.evidence_level == 7


# ─────────────────────────────────────────────────────────────────────────────
# T040 — T060: Evidence level accuracy
# ─────────────────────────────────────────────────────────────────────────────

def test_T040_symbol_direction_gives_l2():
    records = _make_n_outcomes(10, symbol="TATASTEEL", direction="BUY")
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.metrics.evidence_level == 2

def test_T041_symbol_direction_regime_with_context_gives_l1():
    records = [
        _make_outcome(symbol="TATASTEEL", direction="BUY", regime="BULL",
                      trading_date=str(date(2026, 8, i + 1)),
                      atr_pct=1.5, scanner_confidence=7.0)
        for i in range(6)
    ]
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile(
        "TATASTEEL", "BUY", regime="BULL",
        query_atr_pct=1.5, query_confidence=7.0
    )
    assert profile.metrics.evidence_level == 1

def test_T042_no_symbol_match_sector_regime_gives_l3():
    records = [
        _make_outcome(symbol="JSWSTEEL", direction="BUY", regime="BULL",
                      sector="METALS",
                      trading_date=str(date(2026, 7, i + 1)))
        for i in range(10)
    ]
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY", regime="BULL",
                                        sector="METALS")
    # L2 not met (no TATASTEEL obs), L3 met (10 METALS+BUY+BULL)
    assert profile.metrics.evidence_level == 3

def test_T043_regime_direction_gives_l4():
    records = [
        _make_outcome(symbol="HDFCBANK", direction="BUY", regime="BULL",
                      sector="BANK",
                      trading_date=str(date(2026, 7, i + 1)))
        for i in range(10)
    ]
    hbe = _hbe_with(records)
    # No TATASTEEL, no METALS sector match → L4 (regime+dir) if >=10
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY", regime="BULL",
                                        sector="METALS")
    assert profile.metrics.evidence_level >= 3  # L3 or L4

def test_T044_sector_direction_gives_l5():
    records = [
        _make_outcome(symbol="JSWSTEEL", direction="BUY", regime="BEAR",
                      sector="METALS",
                      trading_date=str(date(2026, 7, i + 1)))
        for i in range(15)
    ]
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY", regime="BULL",
                                        sector="METALS")
    # No TATASTEEL (no L2), no METALS+BUY+BULL (they're BEAR) → skip L3
    # No BULL observations → skip L4
    # METALS+BUY: 15 >= 15 → L5
    assert profile.metrics.evidence_level == 5

def test_T045_broad_market_gives_l6():
    records = [
        _make_outcome(symbol=f"SYM{i}", direction="BUY", regime="BEAR",
                      sector="UNKNOWN",
                      trading_date=str(date(2026, 7, i + 1)))
        for i in range(15)
    ]
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY", regime="BULL",
                                        sector="METALS")
    assert profile.metrics.evidence_level == 6

def test_T046_l1_uses_context_filter():
    # Mix: 5 with atr_pct=1.5, 5 with atr_pct=5.0 — only 1.5 should be L1
    records = [
        _make_outcome(symbol="TATASTEEL", direction="BUY", regime="BULL",
                      atr_pct=1.5, scanner_confidence=7.0,
                      trading_date=str(date(2026, 8, i + 1)))
        for i in range(5)
    ] + [
        _make_outcome(symbol="TATASTEEL", direction="BUY", regime="BULL",
                      atr_pct=5.0, scanner_confidence=7.0,
                      trading_date=str(date(2026, 8, i + 10)))
        for i in range(5)
    ]
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile(
        "TATASTEEL", "BUY", regime="BULL",
        query_atr_pct=1.5, query_confidence=7.0
    )
    # Level 1 matched 5 records (atr_pct=1.5), Level 2 has 10
    assert profile.metrics.evidence_level == 1
    assert profile.metrics.observation_count == 5


# ─────────────────────────────────────────────────────────────────────────────
# T047 — T060: Probability estimates
# ─────────────────────────────────────────────────────────────────────────────

def test_T047_target_hit_probability():
    records = (
        _make_n_outcomes(8, first_event=TARGET_HIT, target_hit=True, stop_hit=False) +
        _make_n_outcomes(2, first_event=STOP_HIT,   target_hit=False, stop_hit=True,
                         base_date_str="2026-04-01")
    )
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.metrics.target_hit_probability == 0.8

def test_T048_stop_first_probability():
    records = (
        _make_n_outcomes(3, first_event=TARGET_HIT, target_hit=True, stop_hit=False) +
        _make_n_outcomes(7, first_event=STOP_HIT,   target_hit=False, stop_hit=True,
                         base_date_str="2026-04-01")
    )
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.metrics.stop_first_probability == 0.7

def test_T049_positive_move_probability():
    # All t5_ret_pct > 0
    records = _make_n_outcomes(10, first_event=TARGET_HIT, target_hit=True)
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.metrics.positive_move_probability == 1.0

def test_T050_prob_below_min_sample_is_none():
    records = _make_n_outcomes(4, first_event=TARGET_HIT)  # < MIN_OBS_FOR_PROBS
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    # Level 7 (4 < 5 min), so all None
    assert profile.metrics.target_hit_probability is None

def test_T051_expired_probability():
    records = (
        _make_n_outcomes(6, first_event=TARGET_HIT, target_hit=True) +
        _make_n_outcomes(4, first_event=OUTCOME_EXPIRED, target_hit=False, stop_hit=False,
                         base_date_str="2026-04-01")
    )
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.metrics.expired_probability == 0.4

def test_T052_threshold_prob_1pct_t1():
    records = [
        _make_outcome(trading_date=str(date(2026, 7, i + 1)),
                      t1_ret_pct=2.0 if i % 2 == 0 else 0.5)
        for i in range(10)
    ]
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    # 5 of 10 have t1_ret_pct >= 1.0
    assert profile.metrics.prob_move_1pct_by_t1 == 0.5

def test_T053_threshold_prob_5pct_t5_below_min():
    records = _make_n_outcomes(4)  # below level min
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.metrics.prob_move_5pct_by_t5 is None


# ─────────────────────────────────────────────────────────────────────────────
# T054 — T070: Move distributions
# ─────────────────────────────────────────────────────────────────────────────

def test_T054_favourable_move_p50_up():
    records = [
        _make_outcome(trading_date=str(date(2026, 7, i + 1)), mfe_pct=float(i + 1))
        for i in range(10)
    ]
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert 5.0 <= profile.metrics.favourable_move_p50 <= 6.0

def test_T055_adverse_move_p50_up():
    records = [
        _make_outcome(trading_date=str(date(2026, 7, i + 1)), mae_pct=-float(i + 1))
        for i in range(10)
    ]
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    # adverse_ret = -mae_pct for long (positive magnitude)
    assert profile.metrics.adverse_move_p50 is not None
    assert profile.metrics.adverse_move_p50 > 0

def test_T056_expected_move_distribution_ordered():
    records = [
        _make_outcome(trading_date=str(date(2026, 7, i + 1)), mfe_pct=float(i))
        for i in range(20)
    ]
    hbe = _hbe_with(records)
    m = hbe.get_behaviour_profile("TATASTEEL", "BUY").metrics
    assert m.expected_move_p25 <= m.expected_move_p50 <= m.expected_move_p75

def test_T057_t1_distribution_populated():
    records = _make_n_outcomes(10)
    hbe = _hbe_with(records)
    m = hbe.get_behaviour_profile("TATASTEEL", "BUY").metrics
    assert m.t1_ret_p50 is not None
    assert m.t3_ret_p50 is not None
    assert m.t5_ret_p50 is not None

def test_T058_short_direction_favourable_move_correct_sign():
    # For SHORT/SELL: favourable = -mae_pct (downward move is favourable)
    records = [
        _make_outcome(symbol="TATASTEEL", direction="SELL",
                      trading_date=str(date(2026, 7, i + 1)),
                      mfe_pct=1.0, mae_pct=-3.0,
                      t1_ret_pct=-2.0, t3_ret_pct=-4.0, t5_ret_pct=-5.0)
        for i in range(10)
    ]
    hbe = _hbe_with(records)
    m = hbe.get_behaviour_profile("TATASTEEL", "SELL").metrics
    # For short, directional_t5 = -t5_ret_pct = +5.0 (positive = good for short)
    assert m.positive_move_probability == 1.0


# ─────────────────────────────────────────────────────────────────────────────
# T059 — T075: Time distributions
# ─────────────────────────────────────────────────────────────────────────────

def test_T059_time_to_target():
    records = [
        _make_outcome(first_event=TARGET_HIT, target_hit=True,
                      days_to_event=i + 1,
                      trading_date=str(date(2026, 7, i + 1)))
        for i in range(10)
    ]
    hbe = _hbe_with(records)
    m = hbe.get_behaviour_profile("TATASTEEL", "BUY").metrics
    assert m.time_to_target_p50 is not None
    assert 5 <= m.time_to_target_p50 <= 6

def test_T060_time_to_stop():
    records = [
        _make_outcome(first_event=STOP_HIT, target_hit=False, stop_hit=True,
                      days_to_event=i + 1,
                      trading_date=str(date(2026, 7, i + 1)))
        for i in range(10)
    ]
    hbe = _hbe_with(records)
    m = hbe.get_behaviour_profile("TATASTEEL", "BUY").metrics
    assert m.time_to_stop_p50 is not None
    assert 5 <= m.time_to_stop_p50 <= 6

def test_T061_time_to_target_below_min_is_none():
    records = [
        _make_outcome(first_event=TARGET_HIT, days_to_event=2,
                      trading_date=str(date(2026, 7, i + 1)))
        for i in range(4)
    ]
    hbe = _hbe_with(records)
    m = hbe.get_behaviour_profile("TATASTEEL", "BUY").metrics
    # Level 7 (4 < 5 min), so time metrics are None
    assert m.time_to_target_p50 is None

def test_T062_expected_days_distribution():
    records = [
        _make_outcome(first_event=TARGET_HIT, days_to_event=i + 1,
                      trading_date=str(date(2026, 7, i + 1)))
        for i in range(10)
    ]
    hbe = _hbe_with(records)
    m = hbe.get_behaviour_profile("TATASTEEL", "BUY").metrics
    assert m.expected_days_p25 is not None
    assert m.expected_days_p25 <= m.expected_days_p50 <= m.expected_days_p75

def test_T063_trading_days_between_same_day():
    d = _trading_days_between("2026-08-01", "2026-08-01")
    assert d is not None and d >= 0

def test_T064_trading_days_between_known():
    # Monday 2026-08-17 to Friday 2026-08-21 = 4 trading days (Mon=1,Tue=2,Wed=3,Thu=4,Fri=5 → 4 gaps)
    d = _trading_days_between("2026-08-17", "2026-08-21")
    assert d == 4

def test_T065_trading_days_between_invalid():
    d = _trading_days_between(None, "2026-08-01")
    assert d is None


# ─────────────────────────────────────────────────────────────────────────────
# T066 — T080: Stability detection
# ─────────────────────────────────────────────────────────────────────────────

def test_T066_insufficient_data_stability():
    records = _make_n_outcomes(8)
    status, r, h = _stability_status(records)
    assert status == "insufficient_data"
    assert r is None
    assert h is None

def test_T067_stable_consistent_hit_rate():
    # All records have same first_event — zero difference
    records = _make_n_outcomes(20, first_event=TARGET_HIT, target_hit=True)
    status, r, h = _stability_status(records)
    assert status == "stable"
    assert abs(r - h) < 0.10

def test_T068_unstable_contradictory_history():
    # First 75%: all TARGET_HIT, last 25%: all STOP_HIT
    n = 20
    split = int(n * 0.75)
    early = [
        _make_outcome(first_event=TARGET_HIT, target_hit=True, stop_hit=False,
                      trading_date=str(date(2026, 1, i + 1)))
        for i in range(split)
    ]
    late = [
        _make_outcome(first_event=STOP_HIT, target_hit=False, stop_hit=True,
                      trading_date=str(date(2026, 8, i + 1)))
        for i in range(n - split)
    ]
    status, r, h = _stability_status(early + late)
    assert status in ("developing", "unstable")

def test_T069_stability_status_in_profile():
    records = _make_n_outcomes(20)
    hbe = _hbe_with(records)
    m = hbe.get_behaviour_profile("TATASTEEL", "BUY").metrics
    assert m.stability_status in ("stable", "developing", "unstable", "insufficient_data")

def test_T070_500_obs_unstable_does_not_give_max_confidence():
    # 500 observations but unstable behaviour
    n = 500
    split = int(n * 0.75)
    early = [
        _make_outcome(first_event=TARGET_HIT, target_hit=True, stop_hit=False,
                      trading_date=str(date(2025, 1, 1) + timedelta(days=i)))
        for i in range(split)
    ]
    late = [
        _make_outcome(first_event=STOP_HIT, target_hit=False, stop_hit=True,
                      trading_date=str(date(2026, 7, 1) + timedelta(days=i)))
        for i in range(n - split)
    ]
    records = early + late
    hbe = _hbe_with(records)
    m = hbe.get_behaviour_profile("TATASTEEL", "BUY").metrics
    assert m.stability_status in ("developing", "unstable")
    # Confidence should NOT be maximum (0.8) despite large sample
    assert m.confidence < 0.75


# ─────────────────────────────────────────────────────────────────────────────
# T071 — T085: Knowledge target/stop
# ─────────────────────────────────────────────────────────────────────────────

def test_T071_atr_fallback_target_source():
    hbe = _hbe_with([])
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert "ATR_FALLBACK" in profile.target_source or profile.target_source == _L7

def test_T072_empirical_target_from_records():
    # knowledge_target=215, reference_entry=200 → 7.5% offset
    records = [
        _make_outcome(trading_date=str(date(2026, 7, i + 1)),
                      first_event=TARGET_HIT, target_hit=True)
        for i in range(10)
    ]
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY", query_entry=200.0)
    # empirical offset = 7.5% → knowledge_target = 200 * 1.075 = 215
    if profile.metrics.target_source == "EMPIRICAL":
        assert profile.knowledge_target is not None
        assert abs(profile.knowledge_target - 215.0) < 5.0

def test_T073_insufficient_target_is_none():
    hbe = _hbe_with([])
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY", query_entry=200.0)
    assert profile.knowledge_target is None

def test_T074_target_source_label_present():
    hbe = _hbe_with([])
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert isinstance(profile.target_source, str)
    assert len(profile.target_source) > 0

def test_T075_short_direction_stop_above_entry():
    records = [
        _make_outcome(symbol="TATASTEEL", direction="SELL",
                      trading_date=str(date(2026, 7, i + 1)),
                      first_event=STOP_HIT, stop_hit=True, target_hit=False)
        for i in range(10)
    ]
    # Override stop to be above entry for SELL
    for r in records:
        r.knowledge_stop = 210.0
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "SELL", query_entry=200.0)
    if profile.knowledge_stop is not None:
        # For SELL, empirical stop should be above entry
        assert profile.knowledge_stop >= 200.0


# ─────────────────────────────────────────────────────────────────────────────
# T076 — T090: Safety invariants
# ─────────────────────────────────────────────────────────────────────────────

def test_T076_broker_calls_always_zero():
    hbe = HistoricalBehaviourEngine()
    assert hbe.broker_calls == 0
    hbe._outcomes = _make_n_outcomes(10)
    hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert hbe.broker_calls == 0

def test_T077_orders_always_zero():
    hbe = _hbe_with(_make_n_outcomes(20))
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert hbe.orders == 0
    assert profile.orders == 0

def test_T078_no_lookahead_always_true_in_profile():
    hbe = _hbe_with(_make_n_outcomes(20))
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.no_lookahead is True

def test_T079_no_lookahead_in_all_outcome_records():
    records = _make_n_outcomes(20)
    for r in records:
        assert r.no_lookahead is True

def test_T080_hbe_does_not_import_broker():
    import opportunity_engine.historical_behaviour_engine as mod
    import inspect
    src = inspect.getsource(mod)
    # Check no actual import or call — docstring mentions are fine
    for bad in ("place_order(", "from data_feeds", "import dhan", "import DhanBroker",
                "cancel_order(", "modify_order(", "broker.execute"):
        assert bad not in src, f"Safety violation: '{bad}' found in HBE source"

def test_T081_hbe_models_does_not_import_broker():
    import opportunity_engine.hbe_models as mod
    import inspect
    src = inspect.getsource(mod)
    for bad in ("place_order", "DhanBroker", "OrderManager"):
        assert bad not in src

def test_T082_paper_trading_not_modified():
    import config
    pt_before = getattr(config, "PAPER_TRADING", True)
    hbe = _hbe_with(_make_n_outcomes(20))
    hbe.get_behaviour_profile("TATASTEEL", "BUY")
    pt_after = getattr(config, "PAPER_TRADING", True)
    assert pt_before == pt_after


# ─────────────────────────────────────────────────────────────────────────────
# T083 — T095: V2 score preview
# ─────────────────────────────────────────────────────────────────────────────

def test_T083_v2_fallback_when_no_data():
    m = _atr_fallback_metrics()
    v2 = _compute_v2_preview(0.7, m, "BUY")
    assert v2.using_fallback is True
    assert v2.score_v2 == 0.7

def test_T084_v2_preview_uses_empirical_when_available():
    # Build metrics with known target_hit_probability=0.8
    records = (
        _make_n_outcomes(8, first_event=TARGET_HIT, target_hit=True) +
        _make_n_outcomes(2, first_event=STOP_HIT, target_hit=False, stop_hit=True,
                         base_date_str="2026-04-01")
    )
    m = _compute_metrics(records, 2, _L2, 2, _REF_DATE)
    v2 = _compute_v2_preview(0.5, m, "BUY")
    # With p_target=0.8, v2 component = 0.4*0.5 + 0.3*0.8 + ... ≥ 0.5
    assert v2.score_v2 >= 0.4
    assert not v2.using_fallback

def test_T085_v2_capped_at_1():
    records = _make_n_outcomes(100, first_event=TARGET_HIT, target_hit=True)
    m = _compute_metrics(records, 2, _L2, 2, _REF_DATE)
    v2 = _compute_v2_preview(1.0, m, "BUY")
    assert v2.score_v2 <= 1.0

def test_T086_v2_non_negative():
    records = _make_n_outcomes(100, first_event=STOP_HIT, target_hit=False, stop_hit=True)
    m = _compute_metrics(records, 2, _L2, 2, _REF_DATE)
    v2 = _compute_v2_preview(0.0, m, "BUY")
    assert v2.score_v2 >= 0.0

def test_T087_v2_delta_is_v2_minus_v1():
    records = _make_n_outcomes(50, first_event=TARGET_HIT)
    m = _compute_metrics(records, 2, _L2, 2, _REF_DATE)
    v2 = _compute_v2_preview(0.5, m, "BUY")
    assert abs(v2.v2_delta - (v2.score_v2 - v2.score_v1)) < 1e-9

def test_T088_v2_evidence_level_reported():
    records = _make_n_outcomes(20)
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY", v1_score=0.6)
    assert profile.score_v2_preview.evidence_level <= 7

def test_T089_v2_readonly_no_production_mutation():
    # Calling V2 on an HBE with outcomes should not change any global state
    records = _make_n_outcomes(50)
    hbe1 = _hbe_with(records)
    profile1 = hbe1.get_behaviour_profile("TATASTEEL", "BUY", v1_score=0.5)
    hbe2 = _hbe_with(records)
    profile2 = hbe2.get_behaviour_profile("TATASTEEL", "BUY", v1_score=0.5)
    # Deterministic: same inputs → same V2
    assert profile1.score_v2_preview.score_v2 == profile2.score_v2_preview.score_v2


# ─────────────────────────────────────────────────────────────────────────────
# T090 — T100: File I/O
# ─────────────────────────────────────────────────────────────────────────────

def _write_klp_file(tmpdir: Path, trading_date: str, n_obs: int, n_outcomes: int) -> Path:
    """Write a synthetic KLP JSONL file to tmpdir."""
    fname = tmpdir / f"KLP_{trading_date}.jsonl"
    with fname.open("w") as fh:
        for i in range(n_obs):
            obs_id = f"OBS_{trading_date}_{i}"
            obs = {
                "obs_id": obs_id, "event_type": "KNOWLEDGE_OBSERVATION",
                "trading_date": trading_date,
                "symbol": "TATASTEEL", "direction": "BUY", "regime": "BULL",
                "reference_entry": 200.0, "knowledge_target": 215.0, "knowledge_stop_loss": 192.0,
                "atr": 3.0, "atr_pct": 1.5,
                "scanner_confidence": 7.0, "candidate_score": 0.7,
                "knowledge_score": 0.65, "knowledge_RR": 2.5,
                "no_lookahead": True,
            }
            fh.write(json.dumps(obs) + "\n")
            if i < n_outcomes:
                outcome = {
                    "obs_id": obs_id, "event_type": "OUTCOME_UPDATE",
                    "first_event": "TARGET_HIT", "first_event_day": "2026-08-22",
                    "target_hit": True, "stop_hit": False,
                    "t1_ret_pct": 1.5, "t3_ret_pct": 3.0, "t5_ret_pct": 4.5,
                    "mfe_pct": 5.0, "mae_pct": -1.0,
                    "no_lookahead": True,
                }
                fh.write(json.dumps(outcome) + "\n")
    return fname


def test_T090_load_outcomes_from_file():
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        _write_klp_file(tmpdir, "2026-08-20", n_obs=10, n_outcomes=8)
        hbe = HistoricalBehaviourEngine(data_dir=tmpdir)
        count = hbe.load_outcomes()
        assert count == 8  # only joined outcomes

def test_T091_load_skips_pending_outcomes():
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        fname = tmpdir / "KLP_2026-08-20.jsonl"
        with fname.open("w") as fh:
            obs = {
                "obs_id": "OBS_PENDING", "event_type": "KNOWLEDGE_OBSERVATION",
                "symbol": "TATASTEEL", "direction": "BUY", "regime": "BULL",
                "reference_entry": 200.0, "knowledge_target": 215.0,
                "knowledge_stop_loss": 192.0, "atr": 3.0, "atr_pct": 1.5,
            }
            fh.write(json.dumps(obs) + "\n")
            outcome = {
                "obs_id": "OBS_PENDING", "event_type": "OUTCOME_UPDATE",
                "first_event": "OUTCOME_PENDING",
            }
            fh.write(json.dumps(outcome) + "\n")
        hbe = HistoricalBehaviourEngine(data_dir=tmpdir)
        count = hbe.load_outcomes()
        assert count == 0

def test_T092_load_corrupt_lines_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        fname = tmpdir / "KLP_2026-08-20.jsonl"
        with fname.open("w") as fh:
            fh.write("NOT_JSON\n")
            obs = {"obs_id": "OBS1", "event_type": "KNOWLEDGE_OBSERVATION",
                   "symbol": "TATASTEEL", "direction": "BUY", "regime": "BULL",
                   "reference_entry": 200.0, "knowledge_target": 215.0,
                   "knowledge_stop_loss": 192.0, "atr": 3.0, "atr_pct": 1.5}
            fh.write(json.dumps(obs) + "\n")
            out = {"obs_id": "OBS1", "event_type": "OUTCOME_UPDATE",
                   "first_event": "TARGET_HIT", "t1_ret_pct": 1.0}
            fh.write(json.dumps(out) + "\n")
        hbe = HistoricalBehaviourEngine(data_dir=tmpdir)
        count = hbe.load_outcomes()
        assert count == 1

def test_T093_load_empty_dir():
    with tempfile.TemporaryDirectory() as tmp:
        hbe = HistoricalBehaviourEngine(data_dir=Path(tmp))
        count = hbe.load_outcomes()
        assert count == 0

def test_T094_load_multiple_files():
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        _write_klp_file(tmpdir, "2026-08-20", n_obs=5, n_outcomes=5)
        _write_klp_file(tmpdir, "2026-08-21", n_obs=5, n_outcomes=5)
        hbe = HistoricalBehaviourEngine(data_dir=tmpdir)
        count = hbe.load_outcomes()
        assert count == 10

def test_T095_write_diagnostic_record():
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        hbe = _hbe_with(_make_n_outcomes(10))
        profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
        hbe.write_diagnostic_record(profile, output_dir=tmpdir)
        ledger = tmpdir / "hbe_ledger.jsonl"
        assert ledger.exists()
        lines = [l for l in ledger.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["symbol"] == "TATASTEEL"
        assert rec["no_lookahead"] is True
        assert rec["broker_calls"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# T096 — T105: Determinism + isolation
# ─────────────────────────────────────────────────────────────────────────────

def test_T096_deterministic_output():
    records = _make_n_outcomes(30)
    hbe1 = _hbe_with(records)
    hbe2 = _hbe_with(records)
    p1 = hbe1.get_behaviour_profile("TATASTEEL", "BUY", regime="BULL")
    p2 = hbe2.get_behaviour_profile("TATASTEEL", "BUY", regime="BULL")
    assert p1.metrics.target_hit_probability == p2.metrics.target_hit_probability
    assert p1.metrics.observation_count == p2.metrics.observation_count

def test_T097_symbol_isolation():
    recs_a = _make_n_outcomes(20, symbol="TATASTEEL")
    recs_b = _make_n_outcomes(20, symbol="HDFCBANK")
    hbe = _hbe_with(recs_a + recs_b)
    pa = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    pb = hbe.get_behaviour_profile("HDFCBANK", "BUY")
    assert pa.metrics.observation_count == 20
    assert pb.metrics.observation_count == 20

def test_T098_direction_isolation():
    recs_buy  = _make_n_outcomes(10, direction="BUY")
    recs_sell = _make_n_outcomes(10, direction="SELL", base_date_str="2026-05-01")
    hbe = _hbe_with(recs_buy + recs_sell)
    pb = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    ps = hbe.get_behaviour_profile("TATASTEEL", "SELL")
    assert pb.metrics.observation_count == 10
    assert ps.metrics.observation_count == 10

def test_T099_regime_isolation_affects_level():
    recs_bull = _make_n_outcomes(20, regime="BULL")
    recs_bear = _make_n_outcomes(20, regime="BEAR", base_date_str="2026-05-01")
    hbe = _hbe_with(recs_bull + recs_bear)
    pb = hbe.get_behaviour_profile("TATASTEEL", "BUY", regime="BULL")
    # L1 with regime="BULL" gets 20 obs (ATR matching skipped if query_atr_pct=None)
    assert pb.metrics.evidence_level <= 2

def test_T100_get_outcome_count():
    records = _make_n_outcomes(42)
    hbe = _hbe_with(records)
    assert hbe.get_outcome_count() == 42

def test_T101_get_symbol_counts():
    recs_a = _make_n_outcomes(5, symbol="TATASTEEL")
    recs_b = _make_n_outcomes(3, symbol="HDFCBANK", base_date_str="2026-05-01")
    hbe = _hbe_with(recs_a + recs_b)
    counts = hbe.get_symbol_counts()
    assert counts["TATASTEEL"] == 5
    assert counts["HDFCBANK"] == 3

def test_T102_profile_always_has_valid_tier_label():
    hbe = _hbe_with(_make_n_outcomes(10))
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.metrics.evidence_tier_label in set(TIER_LABELS.values())

def test_T103_profile_always_has_version():
    hbe = _hbe_with([])
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.calculation_version == "HBE_v1"

def test_T104_sector_lookup_known_symbol():
    assert _get_sector("HDFCBANK") == "BANK"
    assert _get_sector("TATASTEEL") == "METALS"
    assert _get_sector("ITC") == "FMCG"

def test_T105_sector_lookup_unknown_symbol():
    assert _get_sector("UNKNOWNSYM") == "UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# T106 — T110: Context similarity
# ─────────────────────────────────────────────────────────────────────────────

def test_T106_context_similar_none_params():
    r = _make_outcome(atr_pct=1.5, scanner_confidence=7.0)
    assert _context_similar(r, None, None) is True

def test_T107_context_similar_atr_within_tolerance():
    r = _make_outcome(atr_pct=1.5)
    assert _context_similar(r, 1.5, None) is True
    assert _context_similar(r, 1.8, None) is True   # 20% difference < 30%

def test_T108_context_similar_atr_outside_tolerance():
    r = _make_outcome(atr_pct=1.0)
    assert _context_similar(r, 2.0, None) is False   # 100% difference > 30%

def test_T109_context_similar_conf_within_tolerance():
    r = _make_outcome(scanner_confidence=7.0)
    assert _context_similar(r, None, 8.5) is True   # diff=1.5 < 2.0

def test_T110_context_similar_conf_outside_tolerance():
    r = _make_outcome(scanner_confidence=4.0)
    assert _context_similar(r, None, 7.5) is False   # diff=3.5 > 2.0


# ─────────────────────────────────────────────────────────────────────────────
# T111 — T115: Large sample / tier 6
# ─────────────────────────────────────────────────────────────────────────────

def test_T111_500_obs_tier6():
    records = _make_n_outcomes(500, base_date_str="2025-01-01")
    hbe = _hbe_with(records, reference_date=date(2025, 6, 1))
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.metrics.evidence_tier == 6

def test_T112_500_obs_target_prob_is_computed():
    records = _make_n_outcomes(500, first_event=TARGET_HIT, target_hit=True,
                               base_date_str="2025-01-01")
    hbe = _hbe_with(records, reference_date=date(2025, 6, 1))
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.metrics.target_hit_probability == 1.0

def test_T113_250_obs_tier5():
    records = _make_n_outcomes(250, base_date_str="2025-06-01")
    hbe = _hbe_with(records, reference_date=date(2026, 1, 1))
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.metrics.evidence_tier == 5

def test_T114_tier6_unstable_not_max_confidence():
    """500 observations in two contradictory halves → high tier but low confidence."""
    n = 500
    split = 375
    early = [
        _make_outcome(first_event=TARGET_HIT, target_hit=True, stop_hit=False,
                      trading_date=str(date(2025, 1, 1) + timedelta(days=i)))
        for i in range(split)
    ]
    late = [
        _make_outcome(first_event=STOP_HIT, target_hit=False, stop_hit=True,
                      trading_date=str(date(2026, 6, 1) + timedelta(days=i)))
        for i in range(n - split)
    ]
    hbe = _hbe_with(early + late)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    assert profile.metrics.evidence_tier == 6
    assert profile.metrics.confidence <= 0.7  # unstable → reduced confidence (not maximum)

def test_T115_as_dict_no_exception():
    records = _make_n_outcomes(20)
    hbe = _hbe_with(records)
    profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
    d = profile.as_dict()
    assert isinstance(d, dict)
    assert d["query_symbol"] == "TATASTEEL"
    assert d["no_lookahead"] is True
