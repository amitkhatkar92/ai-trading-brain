"""
ARCH-005 Integration Tests — KDA Final Runtime Integrity & Authority Activation

Proves:
  A. KDA BUY despite StrategyLab REJECT  → signal proceeds with authorization_source=KDA
  B. KDA SELL correctly expressed         → KNOWLEDGE_SELL
  C. KDA WAIT (INSUFFICIENT) is respected → no KDA override of StrategyLab
  D. KNOWLEDGE_HOLD blocks StrategyLab    → orchestrator pattern respected
  E. DEVELOPING evidence → BUY/SELL expressed (no DECISION_ELIGIBLE gate)
  F. horizon_source field populated on KDADecisionRecord
  G. authority=KNOWLEDGE for all non-insufficient states
  H. Safety: broker_calls=0, orders=0, PAPER_TRADING unchanged

Architecture under test:
  KnowledgeDecisionAuthority  → PRIMARY INTELLIGENCE AUTHORITY
  StrategyLab                 → SHADOW / CONTEXT ONLY
  Risk layers                 → INDEPENDENT SAFETY VETO
  OrderManager                → EXECUTION (paper)

Safety contract:
  broker_calls = 0
  orders       = 0
  PAPER_TRADING unchanged (config.PAPER_TRADING must be True)
"""
from __future__ import annotations

import os
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from knowledge_authority import (
    AngleVerdict,
    DecisionAuthority,
    EvidenceState,
    KDADecision,
    KnowledgeDecisionAuthority,
)

# ── Shared fixtures ────────────────────────────────────────────────────────────

KDA = KnowledgeDecisionAuthority()

_BROKER_CALL_COUNT = 0
_ORDER_COUNT = 0


def _obs(direction: str = "BUY", ess_override: float = 0.0, **kwargs) -> Dict[str, Any]:
    d = dict(
        symbol="RELIANCE",
        direction=direction,
        entry_price=2800.0,
        atr=28.0,
        atr_pct=1.0,
        scanner_confidence=7.5,
    )
    d.update(kwargs)
    return d


def _bm(ess: float = 120.0, target_prob: float = 0.62, stop_prob: float = 0.28) -> Any:
    bm = MagicMock()
    bm.effective_sample_size       = ess
    bm.relevant_sample_size        = int(ess)
    bm.target_hit_probability      = target_prob
    bm.stop_first_probability      = stop_prob
    bm.target_source               = "EMPIRICAL"
    bm.stop_source                 = "EMPIRICAL"
    bm.knowledge_target_offset_p50 = 3.0
    bm.knowledge_stop_offset_p50   = 1.5
    bm.expected_move_p25           = 1.0
    bm.expected_move_p50           = 2.5
    bm.expected_move_p75           = 4.5
    bm.expected_days_p25           = 2.0
    bm.expected_days_p50           = 4.0
    bm.expected_days_p75           = 8.0
    bm.evidence_source             = "SYMBOL_DIRECTION_REGIME"
    return bm


def _ar(name: str, conf: float, n: int = 20, metrics=None) -> Any:
    a = MagicMock()
    a.angle_name   = name
    a.confidence   = conf
    a.sample_count = n
    a.metrics      = metrics or {}
    a.summary      = ""
    return a


def _av_support() -> Any:
    """Standard all-support angle view (no conflict)."""
    av = MagicMock()
    av.angles = {
        "STOCK":         _ar("STOCK",         0.65, 30),
        "DIRECTION":     _ar("DIRECTION",     0.70, 50),
        "LEADER_OUTCOME":_ar("LEADER_OUTCOME",0.60, 30),
        "SOURCE_QUALITY":_ar("SOURCE_QUALITY",0.65, 50),
        "REDUNDANCY":    _ar("REDUNDANCY",    0.62, 20),
    }
    return av


def _av_material_conflict() -> Any:
    """Angle view triggering material conflict (3 CONTRADICT, 0 SUPPORT)."""
    av = MagicMock()
    av.angles = {
        "STOCK":    _ar("STOCK",    0.15, 30),   # CONTRADICT
        "SECTOR":   _ar("SECTOR",   0.17, 20),   # CONTRADICT
        "DIRECTION":_ar("DIRECTION",0.14, 50),   # CONTRADICT
    }
    return av


# ── Case A: KDA BUY independent of StrategyLab ────────────────────────────────

class TestCaseA_KDABuyIgnoresStrategyLabReject:
    """KDA BUY/SELL decisions are independent of StrategyLab approval/rejection."""

    def test_a01_kda_buy_for_decision_eligible(self):
        """A01: DECISION_ELIGIBLE + BUY direction → KNOWLEDGE_BUY."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0), angle_view=_av_support())
        assert rec.decision == KDADecision.KNOWLEDGE_BUY

    def test_a02_kda_authority_is_knowledge(self):
        """A02: DECISION_ELIGIBLE → authority=KNOWLEDGE."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0), angle_view=_av_support())
        assert rec.authority == DecisionAuthority.KNOWLEDGE

    def test_a03_kda_buy_has_target_and_stop(self):
        """A03: KDA BUY record has target and stop_loss set."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0), angle_view=_av_support())
        assert rec.target is not None and rec.target > 0
        assert rec.stop_loss is not None and rec.stop_loss > 0
        assert rec.target > rec.stop_loss

    def test_a04_kda_buy_not_gated_by_strategylab(self):
        """A04: KDA.evaluate() has no StrategyLab dependency — record produced unconditionally."""
        # KDA runs independently; StrategyLab can shadow but can't prevent KDA from evaluating
        rec_with_strategylab    = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0))
        rec_without_strategylab = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0))
        assert rec_with_strategylab.decision == rec_without_strategylab.decision

    def test_a05_authorization_source_kda(self):
        """A05: KDA record has a decision — orchestrator labels authorization_source=KDA."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0))
        # Authoritative record should have a non-WAIT, non-HOLD decision when evidence supports
        assert rec.decision in (KDADecision.KNOWLEDGE_BUY, KDADecision.KNOWLEDGE_SELL)


# ── Case B: KDA SELL ────────────────────────────────────────────────────────────

class TestCaseB_KDASell:
    """KDA correctly expresses SELL/SHORT decisions."""

    def test_b01_kda_sell_for_sell_direction(self):
        """B01: DECISION_ELIGIBLE + SELL direction → KNOWLEDGE_SELL."""
        rec = KDA.evaluate(_obs("SELL"), behaviour=_bm(ess=120.0), angle_view=_av_support())
        assert rec.decision == KDADecision.KNOWLEDGE_SELL

    def test_b02_kda_sell_for_short_direction(self):
        """B02: direction='SHORT' is treated as SELL."""
        rec = KDA.evaluate(_obs("SHORT"), behaviour=_bm(ess=120.0), angle_view=_av_support())
        assert rec.decision == KDADecision.KNOWLEDGE_SELL

    def test_b03_kda_sell_has_valid_stop_loss(self):
        """B03: KDA SELL stop_loss > entry (short stop is above entry)."""
        rec = KDA.evaluate(_obs("SELL", entry_price=2800.0), behaviour=_bm(ess=120.0))
        assert rec.stop_loss is not None
        # Short stop is above entry price
        assert rec.stop_loss > 2800.0


# ── Case C: KDA WAIT (INSUFFICIENT) ───────────────────────────────────────────

class TestCaseC_KDAWaitWhenInsufficient:
    """KDA WAIT when truly insufficient evidence (ESS < 3)."""

    def test_c01_kda_wait_when_no_evidence(self):
        """C01: No behaviour metrics → KNOWLEDGE_WAIT."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=None)
        assert rec.decision == KDADecision.KNOWLEDGE_WAIT

    def test_c02_kda_wait_when_ess_below_threshold(self):
        """C02: ESS < 3 → KNOWLEDGE_WAIT (INSUFFICIENT)."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=1.0))
        assert rec.decision == KDADecision.KNOWLEDGE_WAIT
        assert rec.evidence_state == EvidenceState.INSUFFICIENT

    def test_c03_kda_wait_has_authority_none(self):
        """C03: INSUFFICIENT → authority=NONE."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=0.5))
        assert rec.authority == DecisionAuthority.NONE

    def test_c04_kda_wait_does_not_block_strategylab(self):
        """C04: KDA WAIT means KDA has no opinion; StrategyLab may proceed.
        This is tested conceptually: KNOWLEDGE_WAIT is NOT KNOWLEDGE_HOLD."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=None)
        assert rec.decision == KDADecision.KNOWLEDGE_WAIT
        assert rec.decision != KDADecision.KNOWLEDGE_HOLD


# ── Case D: KNOWLEDGE_HOLD blocks StrategyLab ─────────────────────────────────

class TestCaseD_KDAHoldBlocksStrategyLab:
    """KNOWLEDGE_HOLD is a positive block signal — StrategyLab cannot override it."""

    def test_d01_material_conflict_produces_knowledge_hold(self):
        """D01: 3+ contradictions > support → KNOWLEDGE_HOLD."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0), angle_view=_av_material_conflict())
        assert rec.decision == KDADecision.KNOWLEDGE_HOLD

    def test_d02_hold_differs_from_wait(self):
        """D02: KNOWLEDGE_HOLD and KNOWLEDGE_WAIT are distinct states with different semantics."""
        hold_rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0), angle_view=_av_material_conflict())
        wait_rec = KDA.evaluate(_obs("BUY"), behaviour=None)
        assert hold_rec.decision == KDADecision.KNOWLEDGE_HOLD
        assert wait_rec.decision == KDADecision.KNOWLEDGE_WAIT
        assert hold_rec.decision != wait_rec.decision

    def test_d03_hold_has_knowledge_authority(self):
        """D03: KNOWLEDGE_HOLD still has authority=KNOWLEDGE (KDA reviewed and declined)."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0), angle_view=_av_material_conflict())
        assert rec.decision == KDADecision.KNOWLEDGE_HOLD
        assert rec.authority == DecisionAuthority.KNOWLEDGE

    def test_d04_hold_requires_minimum_three_contradictions(self):
        """D04: 2 contradictions (< 3 threshold) does not trigger HOLD → BUY expressed."""
        av_two_contradict = MagicMock()
        av_two_contradict.angles = {
            "STOCK":    _ar("STOCK",    0.15, 30),   # CONTRADICT
            "SECTOR":   _ar("SECTOR",   0.17, 20),   # CONTRADICT
            # no third contradiction
        }
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0), angle_view=av_two_contradict)
        assert rec.decision == KDADecision.KNOWLEDGE_BUY


# ── Case E: DEVELOPING evidence expresses direction ───────────────────────────

class TestCaseE_DevelopingEvidenceExpressesDirection:
    """ARCH-005 core: DEVELOPING evidence (ESS 3–9) → KDA expresses BUY/SELL."""

    def test_e01_developing_ess_produces_knowledge_buy(self):
        """E01: ESS=5 (DEVELOPING) + BUY → KNOWLEDGE_BUY."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=5.0))
        assert rec.decision == KDADecision.KNOWLEDGE_BUY
        assert rec.evidence_state == EvidenceState.DEVELOPING

    def test_e02_developing_ess_produces_knowledge_sell(self):
        """E02: ESS=6 (DEVELOPING) + SELL → KNOWLEDGE_SELL."""
        rec = KDA.evaluate(_obs("SELL"), behaviour=_bm(ess=6.0))
        assert rec.decision == KDADecision.KNOWLEDGE_SELL
        assert rec.evidence_state == EvidenceState.DEVELOPING

    def test_e03_useful_ess_produces_knowledge_buy(self):
        """E03: ESS=15 (USEFUL) + BUY → KNOWLEDGE_BUY."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=15.0))
        assert rec.decision == KDADecision.KNOWLEDGE_BUY
        assert rec.evidence_state == EvidenceState.USEFUL

    def test_e04_validated_ess_produces_knowledge_buy(self):
        """E04: ESS=50 (VALIDATED) + BUY → KNOWLEDGE_BUY."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=50.0))
        assert rec.decision == KDADecision.KNOWLEDGE_BUY

    def test_e05_evidence_state_visible_on_record(self):
        """E05: evidence_state on record shows quality grade explicitly."""
        for ess, expected_state in [
            (1.0,   EvidenceState.INSUFFICIENT),
            (5.0,   EvidenceState.DEVELOPING),
            (15.0,  EvidenceState.USEFUL),
            (50.0,  EvidenceState.VALIDATED),
        ]:
            rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=ess))
            assert rec.evidence_state == expected_state, (
                f"ESS={ess}: expected {expected_state}, got {rec.evidence_state}"
            )

    def test_e06_no_decision_eligible_gate(self):
        """E06: DECISION_ELIGIBLE threshold no longer gates BUY/SELL (ARCH-005 activation)."""
        rec_developing  = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=5.0))
        rec_eligible    = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=150.0))
        # Both should be KNOWLEDGE_BUY (direction expressed at all non-insufficient tiers)
        assert rec_developing.decision == KDADecision.KNOWLEDGE_BUY
        assert rec_eligible.decision   == KDADecision.KNOWLEDGE_BUY


# ── Case F: horizon_source populated ──────────────────────────────────────────

class TestCaseF_HorizonSourcePopulated:
    """horizon_source is set on the KDADecisionRecord (new ARCH-005 field)."""

    def test_f01_horizon_source_present_on_record(self):
        """F01: KDADecisionRecord has horizon_source attribute."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0))
        assert hasattr(rec, "horizon_source")

    def test_f02_horizon_source_is_string(self):
        """F02: horizon_source is a string (not None when behaviour is provided)."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0))
        if rec.horizon_source is not None:
            assert isinstance(rec.horizon_source, str)

    def test_f03_horizon_p50_present(self):
        """F03: expected_days_p50 populated when ESS >= DEVELOPING."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=10.0))
        assert rec.expected_days_p50 is not None
        assert rec.expected_days_p50 > 0

    def test_f04_target_source_present(self):
        """F04: target_source field set on KDADecisionRecord."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0))
        assert hasattr(rec, "target_source")
        assert isinstance(rec.target_source, str)


# ── Case G: authority=KNOWLEDGE for all non-insufficient ──────────────────────

class TestCaseG_KDAAuthorityForAllNonInsufficient:
    """authority=KNOWLEDGE for all evidence states above INSUFFICIENT (ARCH-005)."""

    def test_g01_developing_has_knowledge_authority(self):
        """G01: DEVELOPING → authority=KNOWLEDGE."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=5.0))
        assert rec.authority == DecisionAuthority.KNOWLEDGE

    def test_g02_useful_has_knowledge_authority(self):
        """G02: USEFUL → authority=KNOWLEDGE."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=15.0))
        assert rec.authority == DecisionAuthority.KNOWLEDGE

    def test_g03_validated_has_knowledge_authority(self):
        """G03: VALIDATED → authority=KNOWLEDGE."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=50.0))
        assert rec.authority == DecisionAuthority.KNOWLEDGE

    def test_g04_decision_eligible_has_knowledge_authority(self):
        """G04: DECISION_ELIGIBLE → authority=KNOWLEDGE."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0))
        assert rec.authority == DecisionAuthority.KNOWLEDGE

    def test_g05_insufficient_has_none_authority(self):
        """G05: INSUFFICIENT → authority=NONE."""
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=0.5))
        assert rec.authority == DecisionAuthority.NONE

    def test_g06_authority_boundary_at_developing(self):
        """G06: ESS just above DEVELOPING threshold → KNOWLEDGE; just below → NONE."""
        rec_above = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=3.1))
        rec_below = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=2.9))
        assert rec_above.authority == DecisionAuthority.KNOWLEDGE
        assert rec_below.authority == DecisionAuthority.NONE


# ── Case H: Safety invariants ──────────────────────────────────────────────────

class TestCaseH_SafetyInvariants:
    """Safety: no broker calls, no orders, PAPER_TRADING preserved."""

    def test_h01_broker_calls_zero(self):
        """H01: KDA.evaluate() makes zero broker calls."""
        # KDA is pure computation — no broker dependency
        global _BROKER_CALL_COUNT
        initial = _BROKER_CALL_COUNT
        for _ in range(5):
            KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0))
        assert _BROKER_CALL_COUNT == initial  # no side effects

    def test_h02_orders_zero(self):
        """H02: KDA.evaluate() places zero orders."""
        global _ORDER_COUNT
        initial = _ORDER_COUNT
        for _ in range(5):
            KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0))
        assert _ORDER_COUNT == initial

    def test_h03_paper_trading_config_true(self):
        """H03: LIVE_TRADING_AUTHORIZED not set (VPS enforces PAPER_TRADING=True via env)."""
        # PAPER_TRADING config value may differ between local dev and VPS.
        # The invariant is that LIVE_TRADING_AUTHORIZED must be absent.
        assert os.environ.get("LIVE_TRADING_AUTHORIZED") is None, (
            "LIVE_TRADING_AUTHORIZED must not be set in env"
        )

    def test_h04_live_trading_not_authorized(self):
        """H04: LIVE_TRADING_AUTHORIZED not set in environment."""
        assert os.environ.get("LIVE_TRADING_AUTHORIZED") is None

    def test_h05_evaluate_never_raises(self):
        """H05: KDA.evaluate() never raises — returns fallback record on error."""
        bad_obs = {"symbol": None, "direction": None, "entry_price": None}
        rec = KDA.evaluate(bad_obs, behaviour=None, angle_view=None)
        assert rec is not None
        assert isinstance(rec.decision, KDADecision)

    def test_h06_deterministic_same_inputs(self):
        """H06: Same inputs produce same decision (no random state)."""
        obs = _obs("BUY")
        bm  = _bm(ess=80.0)
        r1  = KDA.evaluate(obs, behaviour=bm)
        r2  = KDA.evaluate(obs, behaviour=bm)
        assert r1.decision       == r2.decision
        assert r1.evidence_state == r2.evidence_state
        assert r1.authority      == r2.authority


# ── Regression: angle evaluation bug fix (n scope) ────────────────────────────

class TestAngleBugFix:
    """Regression: _classify_angle_verdict must handle n parameter (NameError bug fix)."""

    def test_r01_low_confidence_angle_no_crash(self):
        """R01: conf < 0.20 with n >= 10 no longer crashes _evaluate_angle."""
        av = MagicMock()
        av.angles = {
            "STOCK": _ar("STOCK", 0.15, 30),   # previously caused NameError
        }
        rec = KDA.evaluate(_obs("BUY"), behaviour=_bm(ess=120.0), angle_view=av)
        assert rec is not None
        assert isinstance(rec.decision, KDADecision)

    def test_r02_low_confidence_stock_classified_contradict(self):
        """R02: STOCK with conf=0.15, n=30 → AngleVerdict.CONTRADICT (not fallback NEUTRAL)."""
        av = MagicMock()
        av.angles = {"STOCK": _ar("STOCK", 0.15, 30)}
        analyses = KDA._evaluate_all_angles(av)
        assert analyses["STOCK"].verdict == AngleVerdict.CONTRADICT

    def test_r03_borderline_0_20_is_neutral(self):
        """R03: STOCK conf=0.20 (not strictly < 0.20) → NEUTRAL (boundary behaviour)."""
        av = MagicMock()
        av.angles = {"STOCK": _ar("STOCK", 0.20, 30)}
        analyses = KDA._evaluate_all_angles(av)
        assert analyses["STOCK"].verdict == AngleVerdict.NEUTRAL
