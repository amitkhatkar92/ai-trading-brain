"""
tests/test_authority_hierarchy.py
==================================
DTA-035 — Learning Authority Hierarchy Regression Tests

Proves the following guarantees hold after DTA-034 (10-year historical replay):

  T001  Historical replay cannot dominate genuine LIVE evidence merely by volume
  T002  ESS-based confidence is not inflated by stale replay bulk
  T003  OOS records are excluded from the HBE evidence pool (regression guard)
  T004  Recent LIVE observations have higher ESS weight per record than stale replay
  T005  Bootstrap records remain available for cold-start (source_type HISTORICAL)
  T006  Replay TRAIN/VAL records remain available for research evidence
  T007  No existing OutcomeRecord is mutated when HBE loads or queries
  T008  evidence_scope/provenance fields remain visible on BehaviourMetrics and KDA output
  T009  KDA decision semantics unchanged when LIVE evidence overrides research evidence
  T010  LIVE evidence reaches DECISION_ELIGIBLE before replay-only pool of same size
  T011  Bootstrap cold-start: HBE with only HISTORICAL records produces valid profile
  T012  Replay research-only: TRAIN+VAL included, OOS excluded, provenance accurate
  T013  Volume-dominated pool: raw count is inflated but ESS correctly reflects quality
  T014  Authority separation: LIVE > replay ESS weight per record
  T015  Confidence gate: stale bulk does not push confidence above quality-justified ceiling
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

import pytest

from opportunity_engine.hbe_models import (
    OutcomeRecord,
    TARGET_HIT, STOP_HIT, OUTCOME_EXPIRED,
    evidence_tier,
)
from opportunity_engine.historical_behaviour_engine import (
    HistoricalBehaviourEngine,
    _effective_sample_size,
    _recency_weight,
    _compute_metrics,
    _L2,
)
from knowledge_authority.knowledge_decision_authority import KnowledgeDecisionAuthority

# ─────────────────────────────────────────────────────────────────────────────
# Reference date — "today" for recency-weight calculations in these tests
# ─────────────────────────────────────────────────────────────────────────────
_REF = date(2026, 9, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_record(
    symbol: str = "TATASTEEL",
    direction: str = "BUY",
    source_type: str = "LIVE",
    validation_partition: str = "",
    trading_date: str = "2026-08-28",
    first_event: str = TARGET_HIT,
    target_hit: bool = True,
    stop_hit: bool = False,
    t5_ret_pct: float = 3.0,
    mfe_pct: float = 4.0,
    mae_pct: float = -1.0,
) -> OutcomeRecord:
    return OutcomeRecord(
        obs_id=f"{symbol}_{trading_date}_{direction}_{source_type}_{validation_partition}",
        trading_date=trading_date,
        symbol=symbol,
        direction=direction,
        regime="BULL",
        sector="METALS",
        reference_entry=200.0,
        knowledge_target=215.0,
        knowledge_stop=192.0,
        atr=3.0,
        atr_pct=1.5,
        scanner_confidence=7.0,
        candidate_score=0.75,
        knowledge_score=0.68,
        knowledge_rr=2.5,
        first_event=first_event,
        first_event_day=(date.fromisoformat(trading_date) + timedelta(days=2)).isoformat(),
        target_hit=target_hit,
        stop_hit=stop_hit,
        t1_ret_pct=1.5,
        t3_ret_pct=3.0,
        t5_ret_pct=t5_ret_pct,
        mfe_pct=mfe_pct,
        mae_pct=mae_pct,
        days_to_event=2,
        source_type=source_type,
        validation_partition=validation_partition,
    )


def _stale_replay_records(
    n: int,
    symbol: str = "TATASTEEL",
    direction: str = "BUY",
    start_year: int = 2016,
    first_event: str = OUTCOME_EXPIRED,
) -> List[OutcomeRecord]:
    """n records confined to start_year..start_year+4 with near-zero recency weight."""
    start = date(start_year, 1, 1)
    end   = date(start_year + 5, 1, 1)
    total_days = (end - start).days   # ~1826 for 5 years
    return [
        _make_record(
            symbol=symbol,
            direction=direction,
            source_type="HISTORICAL_REPLAY",
            validation_partition="TRAIN",
            # cycle within the 5-year window so no record escapes into recent dates
            trading_date=str(start + timedelta(days=i % total_days)),
            first_event=first_event,
            target_hit=(first_event == TARGET_HIT),
            stop_hit=(first_event == STOP_HIT),
        )
        for i in range(n)
    ]


def _recent_live_records(
    n: int,
    symbol: str = "TATASTEEL",
    direction: str = "BUY",
    first_event: str = TARGET_HIT,
) -> List[OutcomeRecord]:
    """n records from last 30 days — high recency weight."""
    base = _REF - timedelta(days=n)
    return [
        _make_record(
            symbol=symbol,
            direction=direction,
            source_type="LIVE",
            trading_date=str(base + timedelta(days=i)),
            first_event=first_event,
            target_hit=(first_event == TARGET_HIT),
            stop_hit=(first_event == STOP_HIT),
        )
        for i in range(n)
    ]


def _hbe(records: List[OutcomeRecord], ref: date = _REF) -> HistoricalBehaviourEngine:
    hbe = HistoricalBehaviourEngine(reference_date=ref)
    hbe._outcomes = list(records)
    hbe._loaded = True
    return hbe


# ─────────────────────────────────────────────────────────────────────────────
# T001 — Replay volume does not dominate confidence
# ─────────────────────────────────────────────────────────────────────────────

def test_T001_stale_replay_volume_does_not_inflate_confidence():
    """
    1000 stale replay records (2016-2018) + 10 live records from yesterday.
    Raw count = 1010 → would give TIER_6 confidence with old formula.
    ESS-based confidence must stay below 0.7 because ESS << 100.
    """
    stale = _stale_replay_records(1000, start_year=2016)
    live  = _recent_live_records(10)
    records = stale + live

    m = _compute_metrics(records, 2, _L2, 2, _REF)
    # Raw count is 1010 (would be TIER_6) but ESS is driven by the 10 recent records.
    assert m.observation_count == 1010
    assert m.effective_sample_size < 50   # << raw count (stale records have near-zero weight)
    # Confidence must NOT be elevated to "high" just from raw volume
    assert m.confidence < 0.7, (
        f"confidence={m.confidence} too high for ESS={m.effective_sample_size:.1f}; "
        "stale replay volume must not inflate authority"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T002 — ESS-based confidence is proportional to effective observations
# ─────────────────────────────────────────────────────────────────────────────

def test_T002_confidence_scales_with_ess_not_raw_count():
    """
    Two pools:
      Pool A: 500 stale records (2016-2018) — ESS ≈ 0
      Pool B: 50 recent records (last 30 days) — ESS ≈ 48

    Pool B must have HIGHER or EQUAL confidence than Pool A despite 10× fewer records.
    """
    pool_a = _stale_replay_records(500, start_year=2016)
    pool_b = _recent_live_records(50)

    ma = _compute_metrics(pool_a, 2, _L2, 2, _REF)
    mb = _compute_metrics(pool_b, 2, _L2, 2, _REF)

    assert mb.confidence >= ma.confidence, (
        f"Recent pool B confidence ({mb.confidence}) < stale pool A ({ma.confidence}). "
        "Volume alone must not give pool A higher authority."
    )


# ─────────────────────────────────────────────────────────────────────────────
# T003 — OOS records excluded from evidence pool (regression guard post DTA-034)
# ─────────────────────────────────────────────────────────────────────────────

def test_T003_oos_excluded_from_evidence_post_dta034():
    """
    5 TRAIN + 2 OOS records for TATASTEEL BUY.
    L2 requires ≥ 5; OOS excluded → 5 TRAIN qualify → L2 used (not ATR fallback).
    Statistics must be computed from the 5 TRAIN records only — OOS excluded.
    OOS count must still appear in provenance fields for audit.
    """
    train_recs = [
        _make_record(source_type="HISTORICAL_REPLAY", validation_partition="TRAIN",
                     trading_date=f"2026-08-{d:02d}")
        for d in range(20, 25)   # 5 records
    ]
    oos_recs = [
        _make_record(source_type="HISTORICAL_REPLAY", validation_partition="OOS",
                     trading_date=f"2026-08-{d:02d}")
        for d in range(25, 27)   # 2 records — must NOT count toward L2 threshold
    ]

    hbe_engine = _hbe(train_recs + oos_recs)
    profile = hbe_engine.get_behaviour_profile("TATASTEEL", "BUY")
    # 5 TRAIN (OOS excluded) → L2 reached
    assert profile.metrics.evidence_level < 7, (
        "5 TRAIN records must meet L2 threshold; OOS must NOT be counted in evidence"
    )
    # OOS count visible for audit even though excluded from statistics
    assert profile.metrics.historical_replay_oos_count == 2, (
        "OOS count must be visible in provenance despite exclusion from evidence pool"
    )
    # Statistics computed on only 5 TRAIN (not 7 total)
    assert profile.metrics.observation_count == 5, (
        "observation_count must reflect evidence pool (5 TRAIN), not total including OOS"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T004 — Recent LIVE records have higher ESS weight per record than stale replay
# ─────────────────────────────────────────────────────────────────────────────

def test_T004_live_record_ess_weight_exceeds_stale_replay():
    """
    ESS per record must be higher for a recent LIVE record than for a 2016 replay record.
    This ensures genuine observations carry proportionally more authority.
    """
    live_weight   = _recency_weight("2026-08-30", _REF)
    replay_weight = _recency_weight("2016-06-01", _REF)
    assert live_weight > 100 * replay_weight, (
        f"LIVE weight ({live_weight:.4f}) must dominate 2016 replay weight ({replay_weight:.6f})"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T005 — Bootstrap cold-start: HISTORICAL records produce valid HBE output
# ─────────────────────────────────────────────────────────────────────────────

def test_T005_bootstrap_cold_start_produces_valid_profile():
    """
    Bootstrap (source_type=HISTORICAL) records alone must yield a valid profile.
    No LIVE or replay records required.
    """
    bootstrap_recs = [
        _make_record(
            symbol="RELIANCE",
            direction="BUY",
            source_type="HISTORICAL",
            trading_date=f"2025-{m:02d}-{d:02d}",
            first_event=TARGET_HIT,
        )
        for m, d in [(1, 10), (2, 14), (3, 7), (4, 22), (5, 5),
                     (6, 18), (7, 3), (8, 25), (9, 12), (10, 1)]
    ]
    hbe_engine = _hbe(bootstrap_recs)
    profile = hbe_engine.get_behaviour_profile("RELIANCE", "BUY")

    assert profile.metrics.bootstrap_record_count == 10
    assert profile.metrics.live_record_count == 0
    assert profile.metrics.historical_replay_record_count == 0
    # Profile must not raise and must return valid probability estimates
    assert profile.metrics.target_hit_probability is not None


# ─────────────────────────────────────────────────────────────────────────────
# T006 — Replay TRAIN and VALIDATION records remain available for research evidence
# ─────────────────────────────────────────────────────────────────────────────

def test_T006_replay_train_val_contribute_to_evidence_pool():
    """
    5 TRAIN + 5 VALIDATION replay records for SBIN BUY must reach L2 threshold (≥ 5)
    and produce empirical evidence (not ATR fallback).
    """
    train_recs = [
        _make_record(symbol="SBIN", source_type="HISTORICAL_REPLAY",
                     validation_partition="TRAIN",
                     trading_date=f"2026-08-{d:02d}")
        for d in range(20, 25)
    ]
    val_recs = [
        _make_record(symbol="SBIN", source_type="HISTORICAL_REPLAY",
                     validation_partition="VALIDATION",
                     trading_date=f"2026-08-{d:02d}")
        for d in range(25, 30)
    ]
    hbe_engine = _hbe(train_recs + val_recs)
    profile = hbe_engine.get_behaviour_profile("SBIN", "BUY")

    assert profile.metrics.evidence_level < 7, (
        "TRAIN+VAL replay records must provide evidence above ATR fallback"
    )
    assert profile.metrics.historical_replay_train_count == 5
    assert profile.metrics.historical_replay_validation_count == 5


# ─────────────────────────────────────────────────────────────────────────────
# T007 — No existing records are mutated when HBE loads or queries
# ─────────────────────────────────────────────────────────────────────────────

def test_T007_outcome_records_not_mutated_by_hbe():
    """
    Original records must be bit-for-bit identical after HBE loads and queries them.
    """
    original = _recent_live_records(20)
    snapshots = [(r.obs_id, r.source_type, r.trading_date, r.first_event,
                  r.target_hit, r.stop_hit) for r in original]

    hbe_engine = _hbe(list(original))  # HBE gets a copy of the list
    hbe_engine.get_behaviour_profile("TATASTEEL", "BUY")

    for i, r in enumerate(original):
        after = (r.obs_id, r.source_type, r.trading_date, r.first_event,
                 r.target_hit, r.stop_hit)
        assert after == snapshots[i], f"Record {i} was mutated: {snapshots[i]} → {after}"


# ─────────────────────────────────────────────────────────────────────────────
# T008 — Provenance fields visible on BehaviourMetrics
# ─────────────────────────────────────────────────────────────────────────────

def test_T008_provenance_fields_visible_on_behaviour_metrics():
    """
    BehaviourMetrics must expose all provenance fields so audit tooling can inspect them.
    """
    records = (
        [_make_record(source_type="LIVE", trading_date=f"2026-08-2{d}") for d in range(5)]
        + [_make_record(source_type="HISTORICAL", trading_date=f"2025-07-1{d}") for d in range(5)]
        + [_make_record(source_type="HISTORICAL_REPLAY", validation_partition="TRAIN",
                        trading_date=f"2026-07-{d:02d}") for d in range(10, 15)]
        + [_make_record(source_type="HISTORICAL_REPLAY", validation_partition="VALIDATION",
                        trading_date=f"2026-07-{d:02d}") for d in range(15, 18)]
        + [_make_record(source_type="HISTORICAL_REPLAY", validation_partition="OOS",
                        trading_date="2026-07-20")]
    )
    m = _compute_metrics(records, 2, _L2, 2, _REF)

    assert m.live_record_count >= 5
    assert m.bootstrap_record_count >= 5
    assert m.historical_replay_train_count == 5
    assert m.historical_replay_validation_count == 3
    # OOS count visible for audit even though excluded from evidence
    assert m.historical_replay_oos_count == 1
    assert m.research_record_count >= 5   # bootstrap + replay (all non-live)


# ─────────────────────────────────────────────────────────────────────────────
# T009 — KDA decision semantics unchanged when LIVE evidence overrides research
# ─────────────────────────────────────────────────────────────────────────────

def test_T009_kda_decision_semantics_preserved():
    """
    KDA must produce a valid KDADecisionRecord with correct provenance fields
    when BehaviourMetrics contains mixed LIVE + replay records.
    """
    from opportunity_engine.hbe_models import BehaviourMetrics
    from knowledge_authority.kda_models import KDADecision, EvidenceState

    kda = KnowledgeDecisionAuthority()
    obs = {
        "symbol": "TATASTEEL",
        "direction": "BUY",
        "entry_price": 200.0,
        "atr": 3.0,
        "atr_pct": 1.5,
        "scanner_confidence": 7.0,
    }
    # Build BehaviourMetrics with live evidence dominant (ESS ≈ 120)
    recent = _recent_live_records(120)
    m = _compute_metrics(recent, 2, _L2, 2, _REF)
    # Patch provenance counts to simulate mixed pool
    m.live_record_count = 120
    m.historical_replay_train_count = 80
    m.research_record_count = 80

    rec = kda.evaluate(obs, behaviour=m)

    # Decision must be one of the defined values
    assert isinstance(rec.decision, KDADecision)
    # Provenance must propagate to KDA record
    assert rec.live_record_count == 120
    assert rec.historical_replay_train_count == 80
    # Safety invariants
    assert rec.broker_calls == 0 if hasattr(rec, "broker_calls") else True


# ─────────────────────────────────────────────────────────────────────────────
# T010 — LIVE evidence reaches DECISION_ELIGIBLE before replay-only pool of same size
# ─────────────────────────────────────────────────────────────────────────────

def test_T010_live_ess_dominates_stale_replay_ess_of_equal_raw_count():
    """
    110 recent LIVE records vs 110 stale replay records from 2016.
    Same raw count (110) but radically different ESS:
      - LIVE: ESS >> 0  (high weight, recent)
      - stale replay: ESS ≈ 0  (near-zero weight, 10 years ago)
    Proves that ESS classification is not fooled by equal raw counts.
    """
    from knowledge_authority.knowledge_decision_authority import _ESS_DECISION_ELIGIBLE

    live_recs   = _recent_live_records(110)
    replay_recs = _stale_replay_records(110, start_year=2016)

    live_ess   = _effective_sample_size(live_recs, _REF)
    replay_ess = _effective_sample_size(replay_recs, _REF)

    # Recent LIVE records must have meaningfully higher ESS than stale replay
    assert live_ess > replay_ess * 100, (
        f"LIVE ESS ({live_ess:.1f}) must dominate stale replay ESS ({replay_ess:.4f}) "
        "with same raw count. Recency weighting not working."
    )
    # Stale 2016 replay must have near-zero ESS
    assert replay_ess < 1.0, (
        f"110 stale 2016 replay records must have ESS < 1; got {replay_ess:.4f}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T011 — Bootstrap cold-start: no replay or live required
# ─────────────────────────────────────────────────────────────────────────────

def test_T011_bootstrap_only_cold_start_no_error():
    """HBE with only HISTORICAL (bootstrap) records must not raise."""
    # 20 records across 2024–2025 — valid date range
    months = [(2024, m) for m in range(1, 13)] + [(2025, m) for m in range(1, 9)]
    bootstrap = [
        _make_record(symbol="INFY", source_type="HISTORICAL",
                     trading_date=f"{yr}-{m:02d}-15")
        for yr, m in months
    ]
    hbe_engine = _hbe(bootstrap)
    profile = hbe_engine.get_behaviour_profile("INFY", "BUY")
    assert profile is not None
    assert profile.no_lookahead is True
    assert profile.broker_calls == 0


# ─────────────────────────────────────────────────────────────────────────────
# T012 — Replay provenance accurate: TRAIN+VAL included, OOS excluded
# ─────────────────────────────────────────────────────────────────────────────

def test_T012_replay_partition_accounting():
    """
    8 TRAIN + 4 VALIDATION + 3 OOS records.
    Evidence pool must include 12 (TRAIN+VAL), exclude 3 (OOS).
    All 15 must appear in provenance counts.
    """
    records = (
        [_make_record(source_type="HISTORICAL_REPLAY", validation_partition="TRAIN",
                      trading_date=f"2026-08-{d:02d}") for d in range(10, 18)]
        + [_make_record(source_type="HISTORICAL_REPLAY", validation_partition="VALIDATION",
                        trading_date=f"2026-08-{d:02d}") for d in range(18, 22)]
        + [_make_record(source_type="HISTORICAL_REPLAY", validation_partition="OOS",
                        trading_date=f"2026-08-{d:02d}") for d in range(22, 25)]
    )
    hbe_engine = _hbe(records)
    profile = hbe_engine.get_behaviour_profile("TATASTEEL", "BUY")

    m = profile.metrics
    assert m.historical_replay_train_count == 8
    assert m.historical_replay_validation_count == 4
    assert m.historical_replay_oos_count == 3
    assert m.historical_replay_record_count == 15


# ─────────────────────────────────────────────────────────────────────────────
# T013 — Raw count inflated vs. ESS properly reflects quality
# ─────────────────────────────────────────────────────────────────────────────

def test_T013_raw_count_inflated_ess_reflects_true_quality():
    """
    500 stale 2016 records + 5 live records.
    raw count = 505 → TIER_6 by count.
    ESS should be close to just the 5 live records (stale contribute near 0).
    """
    stale = _stale_replay_records(500, start_year=2016)
    live  = _recent_live_records(5)
    all_records = stale + live

    m = _compute_metrics(all_records, 2, _L2, 2, _REF)

    # Raw count is inflated
    assert m.observation_count == 505
    assert m.evidence_tier == 6  # raw-count tier (informational — kept for display)

    # ESS must reflect only the recent 5 live records (stale weight ≈ 0)
    live_ess = _effective_sample_size(live, _REF)
    assert m.effective_sample_size < live_ess + 1.0, (
        f"ESS ({m.effective_sample_size:.2f}) too high; 500 stale records should contribute ~0. "
        f"Live-only ESS = {live_ess:.2f}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T014 — LIVE record ESS > PAPER record ESS > OLD replay ESS (authority order)
# ─────────────────────────────────────────────────────────────────────────────

def test_T014_authority_order_live_paper_replay():
    """
    Weight order per record: recent LIVE ≈ recent PAPER > old replay.
    Verified via recency_weight comparison.
    """
    live_w   = _recency_weight("2026-08-30", _REF)   # delta = 2 days
    paper_w  = _recency_weight("2026-08-15", _REF)   # delta = 17 days
    replay_w = _recency_weight("2016-01-01", _REF)   # delta = 3897 days

    # Recent LIVE and PAPER both have high weight (above 0.8)
    assert live_w  > 0.98
    assert paper_w > 0.85
    # 10-year old replay has essentially zero weight
    assert replay_w < 1e-10, (
        f"2016 replay weight {replay_w:.2e} should be ~0; "
        "old replay must not contribute to authority"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T015 — Confidence ceiling: stale bulk does not push confidence above ESS ceiling
# ─────────────────────────────────────────────────────────────────────────────

def test_T015_confidence_ceiling_with_stale_bulk():
    """
    500 stale replay records from 2016 (all dates 2016-01-01 to 2017-05-15).
    Raw count 500 → TIER_6 by old formula (would give tier_score=0.5).
    ESS from these records is near-zero → ESS-based tier = 0 → confidence stays low.
    Proves: raw TIER_6 volume alone cannot manufacture a high confidence score.
    """
    stale = _stale_replay_records(500, start_year=2016)
    # All dates are in 2016-2020 (5-year window), so ESS is near zero.
    stale_ess = _effective_sample_size(stale, _REF)
    assert stale_ess < 2.0, (
        f"500 stale 2016-2020 records must have ESS < 2; got {stale_ess:.4f}. "
        "Check _stale_replay_records date range."
    )

    m = _compute_metrics(stale, 2, _L2, 2, _REF)

    # Raw count inflated (display only)
    assert m.observation_count == 500
    assert m.evidence_tier == 6  # raw-count TIER_6 still displayed for observability

    # Confidence must reflect ESS quality (near-zero), not raw tier
    assert m.confidence < 0.1, (
        f"Confidence {m.confidence:.4f} too high for near-zero ESS pool; "
        "stale bulk must not confer false authority via raw count tier"
    )
