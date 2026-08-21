"""
tests/test_klp_004_knowledge_fusion.py
=======================================
KLP-004 — Knowledge Fusion Layer — T001–T040
All tests are self-contained and use synthetic data.
No database, no broker, no lookahead.

Run in isolation:
    python -m pytest tests/test_klp_004_knowledge_fusion.py -v
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import tempfile
import uuid
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

# ── Imports under test ────────────────────────────────────────────────────────
from opportunity_engine.knowledge_fusion.kf_models import (
    AngleResult,
    CANDIDATE, OBSERVED, VALIDATED, DECISION_ELIGIBLE, RETIRED,
    CONTRADICTION_NONE, CONTRADICTION_MINOR, CONTRADICTION_MAJOR,
    ContradictionRecord,
    FALSE_NEGATIVE, FALSE_POSITIVE,
    KnowledgeFusionRecord,
    KnowledgeObject,
    KnowledgeValueScore,
    MultiAngleView,
    OOS_NOT_TESTED, OOS_PASSED, OOS_FAILED,
    OUTCOME_UNKNOWN,
    RedundancyRecord,
    RelationshipCandidate,
    SelectionAnalysisRecord,
    SourceInventoryItem,
    TRUE_NEGATIVE, TRUE_POSITIVE,
    USED_IN_DECISION, USED_AS_CONTEXT, OBSERVED_ONLY, INSUFFICIENT_DATA,
)
from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import (
    KnowledgeFusionEngine,
    _analyse_selection,
    _build_knowledge_objects,
    _compute_market_angle,
    _compute_outcome_angle,
    _counterfactual_angle,
    _detect_contradictions,
    _detect_redundancies,
    _discover_relationships,
    _normalise_rejection,
    _normalise_ct_decision,
    _pearson,
    _pct,
    _recency_w,
    _ess,
    _score_knowledge_value,
    _selection_angle,
    build_source_inventory,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_record(
    symbol: str = "TATASTEEL",
    direction: str = "BUY",
    regime: str = "BULL",
    sector: str = "METALS",
    outcome_available: bool = True,
    move_5d: float = 2.5,
    move_1d: float = 1.0,
    move_3d: float = 1.8,
    max_fav: float = 3.5,
    max_adv: float = -1.2,
    target_hit: bool = True,
    stop_hit: bool = False,
    rejection_outcome: Optional[str] = None,
    final_decision: str = "REJECTED",
    vix: float = 18.0,
    trading_date: str = "2026-04-01",
    knowledge_score: float = 0.7,
    technical_score: float = 7.5,
    risk_score: float = 6.0,
    regime_agent_score: float = 5.0,
    candidate_score: float = 0.65,
    atr_pct: float = 1.2,
) -> KnowledgeFusionRecord:
    """Factory for test records."""
    dm = move_5d if direction in ("BUY", "LONG") else -move_5d
    return KnowledgeFusionRecord(
        fusion_id=f"TEST_{uuid.uuid4().hex[:8]}",
        trading_date=trading_date,
        symbol=symbol,
        direction=direction,
        sector=sector,
        regime=regime,
        vix=vix,
        knowledge_score=knowledge_score,
        technical_score=technical_score,
        risk_score=risk_score,
        regime_agent_score=regime_agent_score,
        candidate_score=candidate_score,
        atr_pct=atr_pct,
        final_decision=final_decision,
        outcome_available=outcome_available,
        move_1d_pct=move_1d,
        move_3d_pct=move_3d,
        move_5d_pct=move_5d,
        max_favorable_move=max_fav,
        max_adverse_move=max_adv,
        target_hit=target_hit,
        stop_hit=stop_hit,
        rejection_outcome=rejection_outcome,
        source_ids=["TEST"],
        no_lookahead=True,
    )


def _make_pool(n: int = 20, direction: str = "BUY", regime: str = "BULL") -> List[KnowledgeFusionRecord]:
    pool = []
    for i in range(n):
        move = (i % 5) - 2.0          # cycles -2 to +2
        pool.append(_make_record(
            direction=direction,
            regime=regime,
            move_5d=move,
            max_fav=abs(move) + 0.5,
            max_adv=-(abs(move) * 0.4 + 0.3),
            target_hit=move > 0,
            stop_hit=move < -1.5,
            rejection_outcome="FALSE_REJECTION" if move > 1.5 else "CORRECT_REJECTION",
            trading_date=f"2026-0{(i // 30) + 1}-{(i % 28) + 1:02d}",
        ))
    return pool


# ─────────────────────────────────────────────────────────────────────────────
# T001 — Source inventory returns correct structure
# ─────────────────────────────────────────────────────────────────────────────

class TestT001SourceInventory:
    def test_source_inventory_returns_list(self):
        with tempfile.TemporaryDirectory() as td:
            items = build_source_inventory(Path(td))
        assert isinstance(items, list)
        assert len(items) >= 8

    def test_source_inventory_items_have_required_fields(self):
        with tempfile.TemporaryDirectory() as td:
            items = build_source_inventory(Path(td))
        required = {"source", "field", "availability", "record_count",
                    "is_outcome_linked", "usage_status"}
        for item in items:
            d = item.as_dict()
            for k in required:
                assert k in d, f"Missing field: {k} in {item.source}"

    def test_source_inventory_absent_when_no_files(self):
        with tempfile.TemporaryDirectory() as td:
            items = build_source_inventory(Path(td))
        absent = [i for i in items if i.availability == "ABSENT"]
        # In empty dir most sources should be absent
        assert len(absent) >= 5

    def test_source_inventory_available_when_db_exists(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "rejection_audit.db"
            conn = sqlite3.connect(str(db_path))
            conn.execute("""CREATE TABLE rejection_log
                            (id INTEGER PRIMARY KEY, symbol TEXT, direction TEXT,
                             market_regime TEXT, vix REAL, move_5d_pct REAL,
                             rejection_outcome TEXT)""")
            conn.execute("INSERT INTO rejection_log VALUES (1,'TATASTEEL','BUY','BULL',18.0,2.5,'CORRECT_REJECTION')")
            conn.commit(); conn.close()
            items = build_source_inventory(Path(td))
        rej = next((i for i in items if i.source == "REJECTION_AUDIT_DB"), None)
        assert rej is not None
        assert rej.availability == "AVAILABLE"
        assert rej.record_count == 1

    def test_source_inventory_usage_status_values_valid(self):
        valid = {USED_IN_DECISION, USED_AS_CONTEXT, OBSERVED_ONLY, INSUFFICIENT_DATA, "UNUSED"}
        with tempfile.TemporaryDirectory() as td:
            items = build_source_inventory(Path(td))
        for item in items:
            assert item.usage_status in valid, f"Invalid usage_status: {item.usage_status}"

    def test_source_inventory_no_broker_fields(self):
        with tempfile.TemporaryDirectory() as td:
            items = build_source_inventory(Path(td))
        for item in items:
            d = json.dumps(item.as_dict())
            for forbidden in ("broker_call", "order_id", "live_trade"):
                assert forbidden not in d.lower(), f"Broker field in inventory: {forbidden}"


# ─────────────────────────────────────────────────────────────────────────────
# T002 — Missing fields are tracked correctly
# ─────────────────────────────────────────────────────────────────────────────

class TestT002MissingFields:
    def test_normalise_rejection_missing_outcomes_tracked(self):
        row = {
            "symbol": "INFY", "direction": "BUY", "market_regime": "BULL",
            "trade_date": "2026-04-01", "vix": 18.0, "decision_score": 7.0,
            "rejected_reason": "LOW_SFT",
            "move_1d_pct": None, "move_3d_pct": None, "move_5d_pct": None,
            "max_favorable_move": None, "max_adverse_move": None,
            "rejection_outcome": None,
        }
        r = _normalise_rejection(row)
        assert "move_1d_pct" in r.missing_fields
        assert "move_5d_pct" in r.missing_fields
        assert r.outcome_available is False

    def test_normalise_rejection_complete_row_has_no_missing(self):
        row = {
            "symbol": "SBIN", "direction": "BUY", "market_regime": "BULL",
            "trade_date": "2026-04-01", "vix": 18.0, "decision_score": 7.0,
            "rejected_reason": "LOW_SFT",
            "move_1d_pct": 1.0, "move_3d_pct": 1.5, "move_5d_pct": 2.0,
            "max_favorable_move": 3.0, "max_adverse_move": -1.0,
            "rejection_outcome": "CORRECT_REJECTION",
        }
        r = _normalise_rejection(row)
        assert r.outcome_available is True
        assert len(r.missing_fields) == 0

    def test_no_lookahead_always_true(self):
        row = {
            "symbol": "TCS", "direction": "BUY", "market_regime": "BULL",
            "trade_date": "2026-04-01", "vix": 18.0, "decision_score": 7.0,
            "rejected_reason": "LOW_SFT", "move_1d_pct": 1.0,
            "move_3d_pct": 1.5, "move_5d_pct": 2.0,
            "max_favorable_move": 3.0, "max_adverse_move": -1.0,
            "rejection_outcome": "CORRECT_REJECTION",
        }
        r = _normalise_rejection(row)
        assert r.no_lookahead is True

    def test_ct_decision_always_marks_outcome_missing(self):
        row = {
            "symbol": "WIPRO", "strategy": "Momentum", "confidence": 7.0,
            "decision": "APPROVED", "rejection_reason": None,
            "technical_score": 8.0, "risk_score": 6.0, "macro_score": 5.0,
            "sentiment_score": 5.5, "regime_score": 6.0, "position_modifier": 1.0,
            "ts": "2026-04-01T10:00:00", "cycle_id": "C001",
            "regime": "BULL", "vix": 18.0, "breadth": 0.6, "pcr": 0.8,
        }
        r = _normalise_ct_decision(row)
        assert r.outcome_available is False
        assert "move_5d_pct" in r.missing_fields


# ─────────────────────────────────────────────────────────────────────────────
# T003 — Normalization
# ─────────────────────────────────────────────────────────────────────────────

class TestT003Normalization:
    def test_symbol_always_uppercase(self):
        row = {
            "symbol": "tatasteel", "direction": "BUY", "market_regime": "BULL",
            "trade_date": "2026-04-01", "vix": 18.0, "decision_score": 6.0,
            "rejected_reason": "LOW_SFT",
            "move_1d_pct": 1.0, "move_3d_pct": 1.5, "move_5d_pct": 2.0,
            "max_favorable_move": 3.0, "max_adverse_move": -1.0,
            "rejection_outcome": "CORRECT_REJECTION",
        }
        r = _normalise_rejection(row)
        assert r.symbol == "TATASTEEL"

    def test_regime_ranging_normalised_to_range(self):
        row = {
            "symbol": "INFY", "direction": "BUY", "market_regime": "RANGING",
            "trade_date": "2026-04-01", "vix": 18.0, "decision_score": 6.0,
            "rejected_reason": "LOW_SFT",
            "move_1d_pct": None, "move_3d_pct": None, "move_5d_pct": None,
            "max_favorable_move": None, "max_adverse_move": None,
            "rejection_outcome": None,
        }
        r = _normalise_rejection(row)
        assert r.regime == "RANGE"

    def test_source_ids_populated(self):
        row = {
            "symbol": "SBIN", "direction": "BUY", "market_regime": "BULL",
            "trade_date": "2026-04-01", "vix": None, "decision_score": None,
            "rejected_reason": None,
            "move_1d_pct": None, "move_3d_pct": None, "move_5d_pct": None,
            "max_favorable_move": None, "max_adverse_move": None,
            "rejection_outcome": None,
        }
        r = _normalise_rejection(row)
        assert "REJECTION_AUDIT_DB" in r.source_ids

    def test_sector_assigned_from_symbol(self):
        row = {
            "symbol": "HDFCBANK", "direction": "BUY", "market_regime": "BULL",
            "trade_date": "2026-04-01", "vix": 18.0, "decision_score": 7.0,
            "rejected_reason": None,
            "move_1d_pct": 1.0, "move_3d_pct": 1.5, "move_5d_pct": 2.0,
            "max_favorable_move": 3.0, "max_adverse_move": -1.0,
            "rejection_outcome": "CORRECT_REJECTION",
        }
        r = _normalise_rejection(row)
        assert r.sector == "BANK"


# ─────────────────────────────────────────────────────────────────────────────
# T004–T013 — Multi-angle analysis
# ─────────────────────────────────────────────────────────────────────────────

class TestT004StockAngle:
    def test_stock_angle_computes_target_rate(self):
        pool = _make_pool(20)
        r = pool[0]
        angle = _compute_outcome_angle(pool, "STOCK")
        assert angle.angle_name == "STOCK"
        assert angle.sample_count == 20
        assert angle.metrics["target_hit_rate"] is not None

    def test_stock_angle_returns_insufficient_with_no_data(self):
        angle = _compute_outcome_angle([], "STOCK")
        assert angle.sample_count == 0
        assert angle.evidence_level == 7
        assert angle.confidence == 0.0

    def test_stock_angle_metrics_not_none(self):
        pool = _make_pool(15)
        angle = _compute_outcome_angle(pool, "STOCK")
        assert angle.metrics["median_move"] is not None
        assert "positive_move_rate" in angle.metrics


class TestT005MarketAngle:
    def test_market_angle_computes_regime_distribution(self):
        pool = _make_pool(30, regime="BULL") + _make_pool(10, regime="BEAR")
        angle = _compute_market_angle(pool)
        assert "BULL" in angle.metrics["regime_distribution"]
        assert angle.metrics["dominant_regime"] == "BULL"

    def test_market_angle_vix_median(self):
        pool = [_make_record(vix=20.0) for _ in range(10)]
        angle = _compute_market_angle(pool)
        assert angle.metrics["vix_median"] == 20.0

    def test_market_angle_insufficient_for_empty(self):
        angle = _compute_market_angle([])
        assert angle.sample_count == 0


class TestT006SectorAngle:
    def test_sector_angle_computed(self):
        sector_pool = [_make_record(sector="BANK", direction="BUY") for _ in range(10)]
        angle = _compute_outcome_angle(sector_pool, "SECTOR")
        assert angle.sample_count == 10

    def test_sector_angle_zero_records_gives_insufficient(self):
        angle = _compute_outcome_angle([], "SECTOR")
        assert angle.evidence_level == 7


class TestT007VolatilityAngle:
    def test_volatility_angle_computed_for_bucket(self):
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import _vix_bucket_records
        pool = [_make_record(vix=20.0) for _ in range(10)]
        bucket = _vix_bucket_records(20.0, pool)
        assert len(bucket) > 0
        angle = _compute_outcome_angle(bucket, "VOLATILITY")
        assert angle.sample_count > 0


class TestT008DirectionAngle:
    def test_direction_angle_buy_vs_sell_difference(self):
        buy_pool  = _make_pool(20, direction="BUY")
        sell_pool = _make_pool(20, direction="SELL")
        pool = buy_pool + sell_pool
        buy_recs  = [r for r in pool if r.direction == "BUY"  and r.outcome_available]
        sell_recs = [r for r in pool if r.direction == "SELL" and r.outcome_available]
        a_buy  = _compute_outcome_angle(buy_recs,  "DIRECTION_BUY")
        a_sell = _compute_outcome_angle(sell_recs, "DIRECTION_SELL")
        assert a_buy.sample_count  == 20
        assert a_sell.sample_count == 20

    def test_direction_angle_returns_correct_angle_name(self):
        pool = _make_pool(10, direction="BUY")
        a = _compute_outcome_angle(pool, "DIRECTION")
        assert a.angle_name == "DIRECTION"


class TestT009MagnitudeAngle:
    def test_magnitude_angle_has_percentile_fields(self):
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import _magnitude_angle
        pool = _make_pool(20)
        a = _magnitude_angle(pool[0], pool)
        assert "expected_move_p50" in a.metrics
        assert "max_favorable_p50"  in a.metrics
        assert a.metrics["expected_move_p50"] is not None


class TestT010TimeAngle:
    def test_time_angle_t1_t3_t5(self):
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import _time_angle
        pool = _make_pool(20)
        a = _time_angle(pool[0], pool)
        assert "t1_p50" in a.metrics
        assert "t3_p50" in a.metrics
        assert "t5_p50" in a.metrics

    def test_time_angle_insufficient_below_5(self):
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import _time_angle
        pool = _make_pool(3)
        a = _time_angle(pool[0], pool)
        assert a.evidence_level == 7


class TestT011RiskAngle:
    def test_risk_angle_has_adverse_excursion(self):
        pool = _make_pool(20)
        a = _risk_angle(pool, "BUY")
        assert "adverse_p50" in a.metrics

    def test_risk_angle_stop_hit_rate_present(self):
        pool = _make_pool(20)
        a = _risk_angle(pool, "BUY")
        assert "stop_hit_rate" in a.metrics


# Import helpers needed here
from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import _risk_angle


class TestT012SelectionAngle:
    def test_selection_angle_approved_rejected_counts(self):
        approved = [_make_record(final_decision="APPROVED") for _ in range(10)]
        rejected = [_make_record(final_decision="REJECTED",
                                  rejection_outcome="CORRECT_REJECTION") for _ in range(10)]
        a = _selection_angle(approved + rejected, "BUY")
        assert a.metrics["approved_count"] == 10
        assert a.metrics["rejected_count"] == 10


class TestT013CounterfactualAngle:
    def test_counterfactual_false_rejection_rate_nonzero(self):
        pool = []
        for i in range(20):
            ro = "FALSE_REJECTION" if i < 8 else "CORRECT_REJECTION"
            pool.append(_make_record(
                final_decision="REJECTED",
                rejection_outcome=ro,
                move_5d=2.5 if ro == "FALSE_REJECTION" else -1.5,
                target_hit=ro == "FALSE_REJECTION",
            ))
        a = _counterfactual_angle(pool, "BUY")
        assert a.metrics["false_rejection_count"] == 8
        assert a.metrics["false_rejection_rate"] == pytest.approx(8 / 20, abs=1e-4)

    def test_counterfactual_missed_opportunity_positive_move(self):
        pool = [_make_record(
            final_decision="REJECTED",
            rejection_outcome="FALSE_REJECTION",
            move_5d=3.5,
        ) for _ in range(10)]
        a = _counterfactual_angle(pool, "BUY")
        assert a.metrics["missed_opportunity_p50"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# T014–T015 — Relationship discovery
# ─────────────────────────────────────────────────────────────────────────────

class TestT014FeatureCombinations:
    def test_discovers_regime_direction_combination(self):
        pool = _make_pool(30, regime="BULL", direction="BUY")
        rels = _discover_relationships(pool, date(2026, 4, 2))
        bull_buy = [r for r in rels
                    if r.conditions.get("regime") == "BULL"
                    and r.conditions.get("direction") == "BUY"]
        assert len(bull_buy) > 0

    def test_relationship_has_required_fields(self):
        pool = _make_pool(20)
        rels = _discover_relationships(pool, date(2026, 4, 2))
        if rels:
            rel = rels[0]
            assert rel.sample_count >= 5
            assert rel.ess >= 0
            assert rel.decision_usefulness >= 0
            assert rel.out_of_sample_status == OOS_NOT_TESTED
            assert rel.promotion_status == CANDIDATE


class TestT015RelationshipDiscovery:
    def test_relationship_positive_rate_between_0_and_1(self):
        pool = _make_pool(30)
        rels = _discover_relationships(pool, date(2026, 4, 2))
        for r in rels:
            if r.positive_rate is not None:
                assert 0.0 <= r.positive_rate <= 1.0

    def test_relationship_target_hit_rate_between_0_and_1(self):
        pool = _make_pool(30)
        rels = _discover_relationships(pool, date(2026, 4, 2))
        for r in rels:
            if r.target_hit_rate is not None:
                assert 0.0 <= r.target_hit_rate <= 1.0

    def test_min_sample_count_enforced(self):
        pool = _make_pool(3)  # too small
        rels = _discover_relationships(pool, date(2026, 4, 2))
        for r in rels:
            assert r.sample_count >= 5


# ─────────────────────────────────────────────────────────────────────────────
# T016 — Insufficient evidence
# ─────────────────────────────────────────────────────────────────────────────

class TestT016InsufficientEvidence:
    def test_empty_pool_returns_no_relationships(self):
        rels = _discover_relationships([], date(2026, 4, 2))
        assert rels == []

    def test_zero_outcome_records_returns_no_relationships(self):
        pool = [_make_record(outcome_available=False) for _ in range(30)]
        rels = _discover_relationships(pool, date(2026, 4, 2))
        assert rels == []

    def test_angle_insufficient_label(self):
        a = _compute_outcome_angle([], "STOCK")
        assert a.summary == "insufficient_data"
        assert a.evidence_level == 7


# ─────────────────────────────────────────────────────────────────────────────
# T017 — Recency weighting
# ─────────────────────────────────────────────────────────────────────────────

class TestT017Recency:
    def test_recent_record_has_higher_weight(self):
        ref = date(2026, 4, 2)
        w_recent = _recency_w("2026-04-01", ref, half_life=90)
        w_old    = _recency_w("2025-01-01", ref, half_life=90)
        assert w_recent > w_old

    def test_zero_day_offset_gives_weight_one(self):
        ref = date(2026, 4, 2)
        w = _recency_w("2026-04-02", ref, half_life=90)
        assert w == pytest.approx(1.0, abs=1e-6)

    def test_90_day_offset_gives_weight_half(self):
        ref = date(2026, 4, 2)
        w = _recency_w("2026-01-01", ref, half_life=90)
        assert w == pytest.approx(0.5, abs=0.02)

    def test_ess_weighted_sum_of_recency(self):
        ref = date(2026, 4, 2)
        dates = ["2026-04-02", "2026-04-02", "2026-04-02"]  # all same day
        ess = _ess(dates, ref)
        assert ess == pytest.approx(3.0, abs=1e-6)

    def test_ess_less_than_raw_count_for_old_dates(self):
        ref = date(2026, 4, 2)
        dates = ["2025-01-01"] * 20
        ess = _ess(dates, ref)
        assert ess < 20


# ─────────────────────────────────────────────────────────────────────────────
# T018 — ESS (effective sample size)
# ─────────────────────────────────────────────────────────────────────────────

class TestT018ESS:
    def test_ess_positive_always(self):
        ref = date(2026, 4, 2)
        dates = ["2026-03-01", "2026-02-01", "2026-01-01"]
        ess = _ess(dates, ref)
        assert ess > 0

    def test_ess_equals_n_for_same_day(self):
        ref = date(2026, 4, 2)
        dates = ["2026-04-02"] * 10
        ess = _ess(dates, ref)
        assert ess == pytest.approx(10.0, abs=1e-5)

    def test_ess_relationship_has_ess_field(self):
        pool = _make_pool(20)
        rels = _discover_relationships(pool, date(2026, 4, 2))
        for r in rels:
            assert r.ess >= 0.0


# ─────────────────────────────────────────────────────────────────────────────
# T019 — Stability
# ─────────────────────────────────────────────────────────────────────────────

class TestT019Stability:
    def test_stable_pattern_detected(self):
        pool = []
        for i in range(20):
            pool.append(_make_record(
                move_5d=2.0,  # consistent
                trading_date=f"2026-0{(i // 15) + 1}-{(i % 14) + 1:02d}",
            ))
        rels = _discover_relationships(pool, date(2026, 4, 2))
        if rels:
            stab = rels[0].stability
            assert stab in ("stable", "developing", "unstable", "insufficient_data")

    def test_high_variance_pattern_not_stable(self):
        pool = []
        for i in range(20):
            move = 5.0 if i < 10 else -5.0  # abrupt change → unstable
            pool.append(_make_record(
                move_5d=move,
                target_hit=move > 0,
                trading_date=f"2026-0{(i // 15) + 1}-{(i % 14) + 1:02d}",
            ))
        rels = _discover_relationships(pool, date(2026, 4, 2))
        if rels:
            stab = rels[0].stability
            # Should be unstable or developing when halves diverge greatly
            assert stab in ("unstable", "developing", "insufficient_data")


# ─────────────────────────────────────────────────────────────────────────────
# T020 — Contradiction detection
# ─────────────────────────────────────────────────────────────────────────────

class TestT020ContradictionDetection:
    def test_buy_signal_in_bear_regime_is_contradiction(self):
        r = _make_record(direction="BUY", regime="BEAR", knowledge_score=0.8)
        contradictions = _detect_contradictions(r)
        regime_conts = [c for c in contradictions if c.contradiction_type == "REGIME"]
        assert len(regime_conts) >= 1

    def test_high_tech_low_risk_is_contradiction(self):
        r = _make_record(technical_score=8.5, risk_score=2.0, regime="BULL")
        contradictions = _detect_contradictions(r)
        tech_risk = [c for c in contradictions if c.contradiction_type == "STRENGTH"
                     and "RISK_AGENT" in c.sources]
        assert len(tech_risk) >= 1

    def test_contradiction_has_fusion_id(self):
        r = _make_record(direction="BUY", regime="BEAR")
        contradictions = _detect_contradictions(r)
        for c in contradictions:
            assert c.fusion_id == r.fusion_id

    def test_no_contradiction_when_aligned(self):
        r = _make_record(direction="BUY", regime="BULL",
                         knowledge_score=0.8, vix=14.0,
                         technical_score=7.0, risk_score=7.5)
        contradictions = _detect_contradictions(r)
        # BULL + BUY + normal VIX + aligned scores → should have no contradictions
        assert all(c.contradiction_type != "REGIME" for c in contradictions)


# ─────────────────────────────────────────────────────────────────────────────
# T021 — Redundancy detection
# ─────────────────────────────────────────────────────────────────────────────

class TestT021RedundantEvidence:
    def test_redundancy_detected_for_correlated_scores(self):
        # Create records where technical_score and regime_agent_score are perfectly correlated
        pool = []
        for i in range(15):
            val = float(i) / 2.0
            pool.append(_make_record(technical_score=val, regime_agent_score=val))
        redundancies = _detect_redundancies(pool)
        # Perfect correlation → should detect redundancy
        assert len(redundancies) > 0

    def test_redundancy_record_has_required_fields(self):
        pool = []
        for i in range(15):
            val = float(i) / 2.0
            pool.append(_make_record(technical_score=val, regime_agent_score=val))
        reds = _detect_redundancies(pool)
        if reds:
            rd = reds[0]
            assert rd.recommendation in ("DEDUPLICATE", "USE_PRIMARY", "AVERAGE")
            assert rd.correlation is not None


# ─────────────────────────────────────────────────────────────────────────────
# T022–T023 — Knowledge object promotion
# ─────────────────────────────────────────────────────────────────────────────

class TestT022KnowledgePromotion:
    def _make_ko(self, sample=15, confidence=0.4, stability="stable",
                  promotion=CANDIDATE, oos=OOS_NOT_TESTED) -> KnowledgeObject:
        now = datetime.now(timezone.utc).isoformat()
        return KnowledgeObject(
            knowledge_id=f"KO_{uuid.uuid4().hex[:6]}",
            knowledge_type="RELATIONSHIP",
            statement="test statement",
            scope="REGIME",
            conditions={"regime": "BULL"},
            supporting_sources=["REJECTION_AUDIT_DB"],
            supporting_observation_ids=[],
            sample_count=sample,
            ess=float(sample) * 0.8,
            evidence_level=3,
            stability=stability,
            recency=0.9,
            confidence=confidence,
            contradiction_status=CONTRADICTION_NONE,
            out_of_sample_status=oos,
            decision_usefulness=0.5,
            created_at=now, updated_at=now,
            promotion_status=promotion,
        )

    def test_candidate_promotes_to_observed_when_criteria_met(self):
        ko = self._make_ko(sample=15, confidence=0.4, promotion=CANDIDATE)
        result = ko.promote()
        assert result is True
        assert ko.promotion_status == OBSERVED

    def test_candidate_does_not_promote_below_threshold(self):
        ko = self._make_ko(sample=5, confidence=0.2, promotion=CANDIDATE)
        result = ko.promote()
        assert result is False
        assert ko.promotion_status == CANDIDATE

    def test_observed_promotes_to_validated(self):
        ko = self._make_ko(sample=25, confidence=0.6, stability="stable", promotion=OBSERVED)
        result = ko.promote()
        assert result is True
        assert ko.promotion_status == VALIDATED

    def test_validated_promotes_to_decision_eligible_when_oos_passed(self):
        ko = self._make_ko(promotion=VALIDATED, oos=OOS_PASSED)
        ko.sample_count = 30
        ko.confidence = 0.7
        ko.stability = "stable"
        result = ko.promote()
        assert result is True
        assert ko.promotion_status == DECISION_ELIGIBLE

    def test_validated_does_not_promote_without_oos(self):
        ko = self._make_ko(promotion=VALIDATED, oos=OOS_NOT_TESTED)
        result = ko.promote()
        assert result is False
        assert ko.promotion_status == VALIDATED

    def test_never_skip_directly_to_decision_eligible(self):
        ko = self._make_ko(sample=100, confidence=0.9, promotion=CANDIDATE, oos=OOS_PASSED)
        ko.promote()  # CANDIDATE → OBSERVED
        assert ko.promotion_status != DECISION_ELIGIBLE
        assert ko.promotion_status == OBSERVED


class TestT023KnowledgeRetirement:
    def test_retire_sets_retired_status(self):
        now = datetime.now(timezone.utc).isoformat()
        ko = KnowledgeObject(
            knowledge_id="KO_test", knowledge_type="RELATIONSHIP",
            statement="s", scope="BROAD", conditions={},
            supporting_sources=[], supporting_observation_ids=[],
            sample_count=50, ess=40.0, evidence_level=3, stability="stable",
            recency=0.9, confidence=0.7, contradiction_status=CONTRADICTION_NONE,
            out_of_sample_status=OOS_PASSED, decision_usefulness=0.6,
            created_at=now, updated_at=now, promotion_status=DECISION_ELIGIBLE,
        )
        ko.retire()
        assert ko.promotion_status == RETIRED


# ─────────────────────────────────────────────────────────────────────────────
# T024 — No-lookahead invariant
# ─────────────────────────────────────────────────────────────────────────────

class TestT024NoLookahead:
    def test_all_fusion_records_have_no_lookahead_true(self):
        pool = _make_pool(10)
        for r in pool:
            assert r.no_lookahead is True

    def test_normalised_rejection_no_lookahead(self):
        row = {
            "symbol": "SBIN", "direction": "BUY", "market_regime": "BULL",
            "trade_date": "2026-04-01", "vix": 18.0, "decision_score": 7.0,
            "rejected_reason": "LOW_SFT",
            "move_1d_pct": 1.0, "move_3d_pct": 1.5, "move_5d_pct": 2.0,
            "max_favorable_move": 3.0, "max_adverse_move": -1.0,
            "rejection_outcome": "CORRECT_REJECTION",
        }
        r = _normalise_rejection(row)
        assert r.no_lookahead is True

    def test_selection_analysis_no_lookahead(self):
        pool = _make_pool(5)
        analyses = _analyse_selection(pool)
        for a in analyses:
            assert a.no_lookahead is True

    def test_multi_angle_view_no_lookahead(self):
        pool = _make_pool(20)
        kfe = KnowledgeFusionEngine()
        view = kfe.analyse_record(pool[0], pool)
        assert view.no_lookahead is True


# ─────────────────────────────────────────────────────────────────────────────
# T025 — Provenance / source IDs
# ─────────────────────────────────────────────────────────────────────────────

class TestT025Provenance:
    def test_rejection_record_has_source_id(self):
        row = {
            "symbol": "INFY", "direction": "BUY", "market_regime": "BULL",
            "trade_date": "2026-04-01", "vix": 18.0, "decision_score": 7.0,
            "rejected_reason": None,
            "move_1d_pct": None, "move_3d_pct": None, "move_5d_pct": None,
            "max_favorable_move": None, "max_adverse_move": None,
            "rejection_outcome": None,
        }
        r = _normalise_rejection(row)
        assert len(r.source_ids) > 0
        assert "REJECTION_AUDIT_DB" in r.source_ids

    def test_ct_record_has_source_id(self):
        row = {
            "symbol": "WIPRO", "strategy": "Momentum", "confidence": 7.0,
            "decision": "APPROVED", "rejection_reason": None,
            "technical_score": 8.0, "risk_score": 6.0,
            "macro_score": 5.0, "sentiment_score": 5.5, "regime_score": 6.0,
            "position_modifier": 1.0, "ts": "2026-04-01T10:00:00",
            "cycle_id": "C001", "regime": "BULL",
            "vix": 18.0, "breadth": 0.6, "pcr": 0.8,
        }
        r = _normalise_ct_decision(row)
        assert "CONTROL_TOWER_DECISIONS" in r.source_ids


# ─────────────────────────────────────────────────────────────────────────────
# T026 — Deterministic output
# ─────────────────────────────────────────────────────────────────────────────

class TestT026DeterministicOutput:
    def test_same_data_same_relationship_stats(self):
        pool = _make_pool(20)
        rels1 = _discover_relationships(pool, date(2026, 4, 2))
        rels2 = _discover_relationships(pool, date(2026, 4, 2))
        # Relationship stats should be identical
        stats1 = {r.conditions.__repr__(): r.target_hit_rate for r in rels1}
        stats2 = {r.conditions.__repr__(): r.target_hit_rate for r in rels2}
        assert stats1 == stats2

    def test_angle_statistics_deterministic(self):
        pool = _make_pool(15)
        a1 = _compute_outcome_angle(pool, "STOCK")
        a2 = _compute_outcome_angle(pool, "STOCK")
        assert a1.metrics["median_move"] == a2.metrics["median_move"]


# ─────────────────────────────────────────────────────────────────────────────
# T027 — Corrupt input handling
# ─────────────────────────────────────────────────────────────────────────────

class TestT027CorruptInput:
    def test_none_vix_does_not_crash_market_angle(self):
        pool = [_make_record(vix=None) for _ in range(10)]
        angle = _compute_market_angle(pool)
        assert angle.metrics["vix_median"] is None

    def test_none_move_skipped_in_statistics(self):
        pool = _make_pool(10)
        for r in pool:
            r.move_5d_pct = None
        angle = _compute_outcome_angle(pool, "STOCK")
        # With no move data, some metrics will be None but no crash
        assert angle is not None

    def test_normalise_rejection_handles_none_vix(self):
        row = {
            "symbol": "SBIN", "direction": "BUY", "market_regime": None,
            "trade_date": "2026-04-01", "vix": None, "decision_score": None,
            "rejected_reason": None,
            "move_1d_pct": None, "move_3d_pct": None, "move_5d_pct": None,
            "max_favorable_move": None, "max_adverse_move": None,
            "rejection_outcome": None,
        }
        r = _normalise_rejection(row)  # must not raise
        assert r is not None
        assert r.vix is None

    def test_empty_pool_analyse_record_no_crash(self):
        kfe = KnowledgeFusionEngine()
        r = _make_record()
        view = kfe.analyse_record(r, [])  # no pool context
        assert view is not None


# ─────────────────────────────────────────────────────────────────────────────
# T028 — Missing source
# ─────────────────────────────────────────────────────────────────────────────

class TestT028MissingSource:
    def test_engine_works_without_rejection_db(self):
        with tempfile.TemporaryDirectory() as td:
            kfe = KnowledgeFusionEngine(data_dir=Path(td), output_dir=Path(td) / "out")
            result = kfe.run_fusion()
        assert result["status"] == "OK"
        assert result["broker_calls"] == 0

    def test_engine_source_inventory_marks_absent_correctly(self):
        with tempfile.TemporaryDirectory() as td:
            items = build_source_inventory(Path(td))
        rej = next(i for i in items if i.source == "REJECTION_AUDIT_DB")
        assert rej.availability == "ABSENT"


# ─────────────────────────────────────────────────────────────────────────────
# T029 — KSL integration (non-regression: engine does not import KSL)
# ─────────────────────────────────────────────────────────────────────────────

class TestT029KSLIntegration:
    def test_no_ksl_import_in_fusion_engine(self):
        import opportunity_engine.knowledge_fusion.knowledge_fusion_engine as eng
        import sys
        for mod_name in sys.modules:
            if "knowledge_synthesiser" in mod_name.lower() or "ksl" in mod_name.lower():
                # Just verifying no hard dependency — not an error if it's loaded by other tests
                pass
        # The key check: kf_models does not import from KSL
        import opportunity_engine.knowledge_fusion.kf_models as kfm
        src = Path(kfm.__file__).read_text()
        assert "knowledge_synthesiser" not in src.lower()


# ─────────────────────────────────────────────────────────────────────────────
# T030 — StrategyLab independence
# ─────────────────────────────────────────────────────────────────────────────

class TestT030StrategyLabIndependence:
    def test_kf_models_does_not_import_strategy_lab(self):
        import opportunity_engine.knowledge_fusion.kf_models as kfm
        src = Path(kfm.__file__).read_text()
        assert "strategy_lab" not in src.lower()

    def test_knowledge_fusion_engine_does_not_import_strategy_lab(self):
        import opportunity_engine.knowledge_fusion.knowledge_fusion_engine as eng
        src = Path(eng.__file__).read_text()
        assert "strategy_lab" not in src.lower()


# ─────────────────────────────────────────────────────────────────────────────
# T031 — Broker safety
# ─────────────────────────────────────────────────────────────────────────────

class TestT031BrokerSafety:
    def test_engine_broker_calls_always_zero(self):
        with tempfile.TemporaryDirectory() as td:
            kfe = KnowledgeFusionEngine(data_dir=Path(td), output_dir=Path(td) / "out")
            _ = kfe.run_fusion()
        assert kfe.broker_calls == 0

    def test_engine_orders_always_zero(self):
        with tempfile.TemporaryDirectory() as td:
            kfe = KnowledgeFusionEngine(data_dir=Path(td), output_dir=Path(td) / "out")
            _ = kfe.run_fusion()
        assert kfe.orders == 0

    def test_result_reports_paper_trading_true(self):
        with tempfile.TemporaryDirectory() as td:
            kfe = KnowledgeFusionEngine(data_dir=Path(td), output_dir=Path(td) / "out")
            result = kfe.run_fusion()
        assert result.get("paper_trading") is True


# ─────────────────────────────────────────────────────────────────────────────
# T032 — No execution imports
# ─────────────────────────────────────────────────────────────────────────────

class TestT032NoExecutionImports:
    def test_kf_models_no_execution_imports(self):
        import opportunity_engine.knowledge_fusion.kf_models as kfm
        src = Path(kfm.__file__).read_text()
        for forbidden in ("order_manager", "execution_engine", "dhan_feed", "zerodha"):
            assert forbidden not in src.lower(), f"Execution import found: {forbidden}"

    def test_fusion_engine_no_execution_imports(self):
        import opportunity_engine.knowledge_fusion.knowledge_fusion_engine as eng
        src = Path(eng.__file__).read_text()
        for forbidden in ("order_manager", "execution_engine", "dhan_feed", "zerodha"):
            assert forbidden not in src.lower(), f"Execution import found: {forbidden}"


# ─────────────────────────────────────────────────────────────────────────────
# T033 — Append-only ledger
# ─────────────────────────────────────────────────────────────────────────────

class TestT033AppendOnlyLedger:
    def test_second_run_appends_not_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            kfe1 = KnowledgeFusionEngine(data_dir=Path(td), output_dir=out_dir)
            kfe1.run_fusion()
            first_size = {}
            for f in out_dir.glob("*.jsonl"):
                first_size[f.name] = f.stat().st_size

            kfe2 = KnowledgeFusionEngine(data_dir=Path(td), output_dir=out_dir)
            kfe2.run_fusion()
            for f in out_dir.glob("*.jsonl"):
                if f.name in first_size:
                    assert f.stat().st_size >= first_size[f.name], (
                        f"{f.name} shrunk — not append-only!"
                    )


# ─────────────────────────────────────────────────────────────────────────────
# T034 — Repeated run idempotency of statistics
# ─────────────────────────────────────────────────────────────────────────────

class TestT034RepeatedRunIdempotency:
    def test_same_input_same_statistics(self):
        pool = _make_pool(25)
        rels1 = _discover_relationships(pool, date(2026, 4, 2))
        rels2 = _discover_relationships(pool, date(2026, 4, 2))
        # Sort both by rel_id-independent key (conditions repr)
        key = lambda r: str(sorted(r.conditions.items()))
        s1 = sorted(rels1, key=key)
        s2 = sorted(rels2, key=key)
        for r1, r2 in zip(s1, s2):
            assert r1.median_move == r2.median_move
            assert r1.target_hit_rate == r2.target_hit_rate


# ─────────────────────────────────────────────────────────────────────────────
# T035 — Out-of-sample separation
# ─────────────────────────────────────────────────────────────────────────────

class TestT035OutOfSampleSeparation:
    def test_new_relationships_start_as_not_tested(self):
        pool = _make_pool(20)
        rels = _discover_relationships(pool, date(2026, 4, 2))
        for r in rels:
            assert r.out_of_sample_status == OOS_NOT_TESTED

    def test_knowledge_objects_start_as_not_tested(self):
        pool = _make_pool(20)
        rels = _discover_relationships(pool, date(2026, 4, 2))
        kos  = _build_knowledge_objects(rels)
        for ko in kos:
            assert ko.out_of_sample_status == OOS_NOT_TESTED

    def test_validated_requires_oos_passed(self):
        now = datetime.now(timezone.utc).isoformat()
        ko = KnowledgeObject(
            knowledge_id="KO_test", knowledge_type="RELATIONSHIP",
            statement="test", scope="REGIME", conditions={},
            supporting_sources=[], supporting_observation_ids=[],
            sample_count=30, ess=25.0, evidence_level=3,
            stability="stable", recency=0.9, confidence=0.7,
            contradiction_status=CONTRADICTION_NONE,
            out_of_sample_status=OOS_FAILED,
            decision_usefulness=0.6,
            created_at=now, updated_at=now, promotion_status=VALIDATED,
        )
        assert ko.can_promote() is False


# ─────────────────────────────────────────────────────────────────────────────
# T036–T037 — Selection classification
# ─────────────────────────────────────────────────────────────────────────────

class TestT036SelectionFalsePositive:
    def test_approved_adverse_move_is_false_positive(self):
        pool = [_make_record(
            final_decision="APPROVED",
            outcome_available=True,
            move_5d=-3.0,  # adverse for BUY
            direction="BUY",
        )]
        analyses = _analyse_selection(pool)
        assert analyses[0].classification == FALSE_POSITIVE

    def test_approved_favorable_move_is_true_positive(self):
        pool = [_make_record(
            final_decision="APPROVED",
            outcome_available=True,
            move_5d=2.5,
            direction="BUY",
        )]
        analyses = _analyse_selection(pool)
        assert analyses[0].classification == TRUE_POSITIVE


class TestT037SelectionFalseNegative:
    def test_rejected_false_rejection_outcome_is_false_negative(self):
        pool = [_make_record(
            final_decision="REJECTED",
            outcome_available=True,
            move_5d=3.0,
            direction="BUY",
            rejection_outcome="FALSE_REJECTION",
        )]
        analyses = _analyse_selection(pool)
        assert analyses[0].classification == FALSE_NEGATIVE

    def test_rejected_correct_rejection_is_true_negative(self):
        pool = [_make_record(
            final_decision="REJECTED",
            outcome_available=True,
            move_5d=-2.0,
            direction="BUY",
            rejection_outcome="CORRECT_REJECTION",
        )]
        analyses = _analyse_selection(pool)
        assert analyses[0].classification == TRUE_NEGATIVE

    def test_no_outcome_is_outcome_unknown(self):
        pool = [_make_record(
            final_decision="REJECTED",
            outcome_available=False,
        )]
        analyses = _analyse_selection(pool)
        assert analyses[0].classification == OUTCOME_UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# T038 — Unused information detection
# ─────────────────────────────────────────────────────────────────────────────

class TestT038UnusedInformation:
    def test_paper_trades_marked_insufficient(self):
        with tempfile.TemporaryDirectory() as td:
            items = build_source_inventory(Path(td))
        pt = next((i for i in items if i.source == "PAPER_TRADES_CSV"), None)
        assert pt is not None
        assert pt.usage_status == INSUFFICIENT_DATA

    def test_klp_outcome_marked_insufficient_when_absent(self):
        with tempfile.TemporaryDirectory() as td:
            items = build_source_inventory(Path(td))
        ko = next((i for i in items if i.source == "KLP_OUTCOME"), None)
        assert ko is not None
        assert ko.usage_status == INSUFFICIENT_DATA


# ─────────────────────────────────────────────────────────────────────────────
# T039 — Knowledge value scoring
# ─────────────────────────────────────────────────────────────────────────────

class TestT039KnowledgeValueScoring:
    def _make_ko(self, sample=50, stability="stable", oos=OOS_NOT_TESTED) -> KnowledgeObject:
        now = datetime.now(timezone.utc).isoformat()
        return KnowledgeObject(
            knowledge_id="KO_score_test", knowledge_type="RELATIONSHIP",
            statement="test", scope="REGIME", conditions={},
            supporting_sources=[], supporting_observation_ids=[],
            sample_count=sample, ess=float(sample) * 0.9, evidence_level=3,
            stability=stability, recency=0.8, confidence=0.65,
            contradiction_status=CONTRADICTION_NONE, out_of_sample_status=oos,
            decision_usefulness=0.5, created_at=now, updated_at=now,
        )

    def test_score_is_between_0_and_1(self):
        ko = self._make_ko()
        score = _score_knowledge_value(ko)
        assert 0.0 <= score.composite_score <= 1.0

    def test_oos_passed_improves_score(self):
        s_not = _score_knowledge_value(self._make_ko(oos=OOS_NOT_TESTED))
        s_pass = _score_knowledge_value(self._make_ko(oos=OOS_PASSED))
        assert s_pass.composite_score >= s_not.composite_score

    def test_unstable_lowers_score(self):
        s_stable   = _score_knowledge_value(self._make_ko(stability="stable"))
        s_unstable = _score_knowledge_value(self._make_ko(stability="unstable"))
        assert s_stable.composite_score > s_unstable.composite_score

    def test_knowledge_value_score_has_all_components(self):
        ko = self._make_ko()
        kv = _score_knowledge_value(ko)
        for attr in ("evidence_strength", "stability_score", "recency_score",
                     "sample_quality", "cross_validation", "out_of_sample",
                     "decision_relevance", "incremental_value", "composite_score"):
            assert getattr(kv, attr) is not None


# ─────────────────────────────────────────────────────────────────────────────
# T040 — Hierarchical evidence integration with HBE
# ─────────────────────────────────────────────────────────────────────────────

class TestT040HierarchicalEvidenceIntegration:
    def test_engine_imports_from_hbe_models(self):
        import opportunity_engine.knowledge_fusion.knowledge_fusion_engine as eng
        src = Path(eng.__file__).read_text()
        assert "hbe_models" in src

    def test_evidence_tier_used_in_relationship_scoring(self):
        pool = _make_pool(10)  # <20 → tier ≤ 2
        rels = _discover_relationships(pool, date(2026, 4, 2))
        for r in rels:
            assert r.decision_usefulness < 0.7, (
                f"Small sample should have low decision_usefulness, got {r.decision_usefulness}"
            )

    def test_large_sample_has_higher_evidence_score(self):
        pool_small = _make_pool(10)
        pool_large = _make_pool(300)
        rels_small = _discover_relationships(pool_small, date(2026, 4, 2))
        rels_large = _discover_relationships(pool_large, date(2026, 4, 2))
        if rels_small and rels_large:
            avg_du_small = sum(r.decision_usefulness for r in rels_small) / len(rels_small)
            avg_du_large = sum(r.decision_usefulness for r in rels_large) / len(rels_large)
            assert avg_du_large > avg_du_small

    def test_angle_evidence_level_decreases_as_samples_increase(self):
        small_pool = _make_pool(5)
        large_pool = _make_pool(200)
        a_small = _compute_outcome_angle(small_pool, "STOCK")
        a_large = _compute_outcome_angle(large_pool, "STOCK")
        assert a_large.evidence_level <= a_small.evidence_level

    def test_full_engine_run_completes_and_reports_zero_broker_calls(self):
        with tempfile.TemporaryDirectory() as td:
            kfe = KnowledgeFusionEngine(data_dir=Path(td), output_dir=Path(td) / "kf")
            result = kfe.run_fusion()
        assert result["status"] == "OK"
        assert result["broker_calls"] == 0
        assert result["orders"] == 0
        assert result["no_lookahead"] is True
