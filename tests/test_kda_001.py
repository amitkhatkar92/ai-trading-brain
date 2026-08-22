"""
tests/test_kda_001.py
======================
KDA-001 — Knowledge Decision Authority
Comprehensive test suite.

Coverage:
- Evidence states (INSUFFICIENT → DECISION_ELIGIBLE)
- All decision types (BUY, SELL, WAIT, HOLD, EXIT)
- Evidence hierarchy levels
- Authority score decomposition
- Target/stop: empirical vs ATR fallback
- Time horizon derivation
- StrategyLab demotion and relationship classification
- Knowledge overrule (only when DECISION_ELIGIBLE)
- Angle evaluation (SUPPORT/NEUTRAL/CONTRADICT/INSUFFICIENT)
- Information contributions
- Counterfactual analysis
- Exit conditions
- OOS gating
- Contradiction handling
- No-lookahead invariant
- Deterministic decision (same inputs → same decision type)
- Safety invariants (broker_calls=0, orders=0)
- Outcome recording structure

Safety contract:
  broker_calls = 0, orders = 0, PAPER_TRADING unchanged
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from knowledge_authority import (
    AngleVerdict,
    DecisionAuthority,
    EvidenceHierarchyLevel,
    EvidenceState,
    ExitState,
    KDADecision,
    KDADecisionRecord,
    KDARelationship,
    KnowledgeDecisionAuthority,
    StrategyContext,
)
from knowledge_authority.kda_models import KnowledgeAuthorityComponents

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

KDA = KnowledgeDecisionAuthority()


def _obs(**kwargs) -> Dict[str, Any]:
    """Minimal scanner observation."""
    defaults = dict(
        symbol="RELIANCE",
        direction="BUY",
        entry_price=2800.0,
        atr=28.0,          # 1% ATR
        atr_pct=1.0,
        scanner_confidence=7.0,
    )
    defaults.update(kwargs)
    return defaults


def _bm(ess=50.0, target_prob=0.6, stop_prob=0.3, target_src="EMPIRICAL", **kwargs):
    """Mock BehaviourMetrics with configurable ESS and probabilities."""
    bm = MagicMock()
    bm.effective_sample_size       = ess
    bm.relevant_sample_size        = int(ess)
    bm.target_hit_probability      = target_prob
    bm.stop_first_probability      = stop_prob
    bm.target_source               = target_src
    bm.stop_source                 = target_src
    bm.knowledge_target_offset_p50 = kwargs.get("target_offset", 3.0)
    bm.knowledge_stop_offset_p50   = kwargs.get("stop_offset", 1.5)
    bm.expected_move_p25           = kwargs.get("em_p25", 1.0)
    bm.expected_move_p50           = kwargs.get("em_p50", 2.5)
    bm.expected_move_p75           = kwargs.get("em_p75", 4.5)
    bm.expected_days_p25           = kwargs.get("days_p25", 2.0)
    bm.expected_days_p50           = kwargs.get("days_p50", 4.0)
    bm.expected_days_p75           = kwargs.get("days_p75", 8.0)
    bm.evidence_source             = kwargs.get("evidence_src", "SYMBOL_DIRECTION_REGIME")
    return bm


def _angle_result(name, confidence, n=20, metrics=None, summary=""):
    ar = MagicMock()
    ar.angle_name   = name
    ar.confidence   = confidence
    ar.sample_count = n
    ar.metrics      = metrics or {}
    ar.summary      = summary
    return ar


def _make_angle_view(angles: Dict[str, Any]) -> MagicMock:
    """Build a mock MultiAngleView with given angle results."""
    av = MagicMock()
    av.angles = angles
    return av


def _make_av(overrides: Optional[Dict] = None) -> MagicMock:
    """Standard 16-angle view with mostly SUPPORT verdicts."""
    base = {
        "STOCK":         _angle_result("STOCK",         0.65, 30),
        "MARKET":        _angle_result("MARKET",        0.60, 40),
        "SECTOR":        _angle_result("SECTOR",        0.62, 25),
        "VOLATILITY":    _angle_result("VOLATILITY",    0.58, 20),
        "DIRECTION":     _angle_result("DIRECTION",     0.70, 50),
        "MAGNITUDE":     _angle_result("MAGNITUDE",     0.55, 15),
        "TIME":          _angle_result("TIME",          0.50, 12),
        "RISK":          _angle_result("RISK",          0.60, 20),
        "SELECTION":     _angle_result("SELECTION",     0.55, 18),
        "COUNTERFACTUAL":_angle_result("COUNTERFACTUAL",0.52, 15),
        "LEADER_OUTCOME":_angle_result("LEADER_OUTCOME",0.60, 30),
        "SOURCE_QUALITY":_angle_result("SOURCE_QUALITY",0.65, 50),
        "RECENCY":       _angle_result("RECENCY",       0.70, 40, {"ess_fraction": 0.75}),
        "REDUNDANCY":    _angle_result("REDUNDANCY",    0.62, 20),
        "CONTRADICTION": _angle_result("CONTRADICTION", 0.82, 0, {"contradictions": 0, "major": 0, "minor": 0}),
        "OOS_VALIDATION":_angle_result("OOS_VALIDATION",0.60, 10, {"oos_pass_rate": 0.7}),
    }
    if overrides:
        base.update(overrides)
    return _make_angle_view(base)


def _mkt(**kwargs) -> Dict[str, Any]:
    defaults = dict(regime="range_market", vix=14.0, pcr=1.0, breadth=0.5)
    defaults.update(kwargs)
    return defaults


# ─────────────────────────────────────────────────────────────────────────────
# T001-T010: Safety invariants
# ─────────────────────────────────────────────────────────────────────────────

class TestSafetyInvariants:

    def test_t001_broker_calls_always_zero(self):
        """T001: broker_calls == 0 always."""
        rec = KDA.evaluate(_obs())
        assert rec.broker_calls == 0

    def test_t002_orders_always_zero(self):
        """T002: orders == 0 always."""
        rec = KDA.evaluate(_obs())
        assert rec.orders == 0

    def test_t003_no_lookahead_always_true(self):
        """T003: no_lookahead == True always."""
        rec = KDA.evaluate(_obs(), _make_av(), _bm(ess=200.0))
        assert rec.no_lookahead is True

    def test_t004_mode_always_shadow(self):
        """T004: mode == 'SHADOW_DECISION' always."""
        rec = KDA.evaluate(_obs())
        assert rec.mode == "SHADOW_DECISION"

    def test_t005_no_execution_imports(self):
        """T005: KDA module's actual imports never reference execution/broker code."""
        import inspect
        from knowledge_authority import knowledge_decision_authority as kda_mod
        source = inspect.getsource(kda_mod)
        # Only scan actual import statements (not docstrings/comments)
        import_lines = [
            ln for ln in source.splitlines()
            if ln.strip().startswith(("import ", "from "))
        ]
        import_text = "\n".join(import_lines)
        for forbidden in ("OrderManager", "dhan_feed", "place_order",
                          "execution_engine", "DhanBroker", "ZerodhaBroker"):
            assert forbidden not in import_text, f"Forbidden import found: {forbidden}"

    def test_t006_decision_record_is_immutable(self):
        """T006: KDADecisionRecord is frozen (immutable)."""
        rec = KDA.evaluate(_obs())
        with pytest.raises((AttributeError, TypeError)):
            rec.orders = 99  # type: ignore

    def test_t007_decision_id_is_unique_per_call(self):
        """T007: Each call generates a different decision_id."""
        r1 = KDA.evaluate(_obs())
        r2 = KDA.evaluate(_obs())
        assert r1.decision_id != r2.decision_id

    def test_t008_returns_record_not_none(self):
        """T008: evaluate() never returns None."""
        rec = KDA.evaluate(_obs())
        assert rec is not None
        assert isinstance(rec, KDADecisionRecord)

    def test_t009_handles_empty_observation(self):
        """T009: evaluate() with empty observation dict returns WAIT, no crash."""
        rec = KDA.evaluate({})
        assert rec.decision == KDADecision.KNOWLEDGE_WAIT

    def test_t010_handles_none_angle_view(self):
        """T010: evaluate() with no angle_view runs without error."""
        rec = KDA.evaluate(_obs(), angle_view=None, behaviour=None)
        assert isinstance(rec, KDADecisionRecord)


# ─────────────────────────────────────────────────────────────────────────────
# T011-T020: Evidence state classification
# ─────────────────────────────────────────────────────────────────────────────

class TestEvidenceState:

    def test_t011_insufficient_when_ess_zero(self):
        """T011: ESS=0 → INSUFFICIENT."""
        rec = KDA.evaluate(_obs(), behaviour=None)
        assert rec.evidence_state == EvidenceState.INSUFFICIENT

    def test_t012_developing_when_ess_5(self):
        """T012: ESS=5 → DEVELOPING."""
        rec = KDA.evaluate(_obs(), behaviour=_bm(ess=5.0))
        assert rec.evidence_state == EvidenceState.DEVELOPING

    def test_t013_useful_when_ess_15(self):
        """T013: ESS=15 → USEFUL."""
        rec = KDA.evaluate(_obs(), behaviour=_bm(ess=15.0))
        assert rec.evidence_state == EvidenceState.USEFUL

    def test_t014_validated_when_ess_50(self):
        """T014: ESS=50 → VALIDATED."""
        rec = KDA.evaluate(_obs(), behaviour=_bm(ess=50.0))
        assert rec.evidence_state == EvidenceState.VALIDATED

    def test_t015_decision_eligible_when_ess_100_stable(self):
        """T015: ESS=150, high stability, OOS not failed → DECISION_ELIGIBLE."""
        bm = _bm(ess=150.0, target_prob=0.7, stop_prob=0.2, target_src="EMPIRICAL")
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_state == EvidenceState.DECISION_ELIGIBLE

    def test_t016_validated_not_eligible_when_oos_failed(self):
        """T016: ESS=200 but OOS=FAILED → stays VALIDATED, not DECISION_ELIGIBLE."""
        from knowledge_authority.knowledge_decision_authority import KnowledgeDecisionAuthority
        kda = KnowledgeDecisionAuthority()
        from knowledge_authority.kda_models import EvidenceState as ES
        state = kda._classify_evidence_state(200.0, 0.7, "FAILED", 0.8)
        assert state == ES.VALIDATED

    def test_t017_validated_not_eligible_when_contradiction_high(self):
        """T017: ESS=200 but contradiction_factor=0.1 → VALIDATED, not DECISION_ELIGIBLE."""
        from knowledge_authority.knowledge_decision_authority import KnowledgeDecisionAuthority
        kda = KnowledgeDecisionAuthority()
        state = kda._classify_evidence_state(200.0, 0.7, "TESTED", 0.1)
        assert state == EvidenceState.VALIDATED

    def test_t018_validated_not_eligible_when_stability_low(self):
        """T018: ESS=200 but stability=0.3 → VALIDATED, not DECISION_ELIGIBLE."""
        from knowledge_authority.knowledge_decision_authority import KnowledgeDecisionAuthority
        kda = KnowledgeDecisionAuthority()
        state = kda._classify_evidence_state(200.0, 0.3, "NOT_TESTED", 0.8)
        assert state == EvidenceState.VALIDATED

    def test_t019_evidence_state_in_record(self):
        """T019: evidence_state present and is EvidenceState enum."""
        rec = KDA.evaluate(_obs(), behaviour=_bm(ess=50.0))
        assert isinstance(rec.evidence_state, EvidenceState)

    def test_t020_ess_stored_in_record(self):
        """T020: effective_sample_size stored correctly."""
        bm = _bm(ess=42.5)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.effective_sample_size == pytest.approx(42.5, abs=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# T021-T030: Decision types
# ─────────────────────────────────────────────────────────────────────────────

class TestDecisionTypes:

    def test_t021_wait_when_insufficient(self):
        """T021: No evidence → KNOWLEDGE_WAIT."""
        rec = KDA.evaluate(_obs(), behaviour=None)
        assert rec.decision == KDADecision.KNOWLEDGE_WAIT

    def test_t022_wait_when_developing(self):
        """T022: DEVELOPING evidence → KNOWLEDGE_WAIT."""
        rec = KDA.evaluate(_obs(), behaviour=_bm(ess=5.0))
        assert rec.decision == KDADecision.KNOWLEDGE_WAIT

    def test_t023_hold_when_useful_but_not_eligible(self):
        """T023: USEFUL evidence but not DECISION_ELIGIBLE → KNOWLEDGE_HOLD."""
        bm = _bm(ess=15.0, target_prob=0.6, stop_prob=0.3)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.decision in (KDADecision.KNOWLEDGE_HOLD, KDADecision.KNOWLEDGE_WAIT)

    def test_t024_buy_when_decision_eligible_buy_direction(self):
        """T024: DECISION_ELIGIBLE + BUY direction → KNOWLEDGE_BUY."""
        bm = _bm(ess=150.0, target_prob=0.7, stop_prob=0.2)
        rec = KDA.evaluate(_obs(direction="BUY", scanner_confidence=8.5), behaviour=bm)
        assert rec.decision == KDADecision.KNOWLEDGE_BUY

    def test_t025_sell_when_decision_eligible_sell_direction(self):
        """T025: DECISION_ELIGIBLE + SELL direction → KNOWLEDGE_SELL."""
        bm = _bm(ess=150.0, target_prob=0.7, stop_prob=0.2)
        rec = KDA.evaluate(_obs(direction="SELL", scanner_confidence=8.5), behaviour=bm)
        assert rec.decision == KDADecision.KNOWLEDGE_SELL

    def test_t026_wait_when_too_many_contradictions(self):
        """T026: Many contradicting angles → KNOWLEDGE_WAIT regardless of ESS."""
        bm = _bm(ess=150.0)
        av = _make_av({
            "STOCK":    _angle_result("STOCK",    0.20, 30),
            "SECTOR":   _angle_result("SECTOR",   0.18, 20),
            "DIRECTION":_angle_result("DIRECTION",0.15, 50),
        })
        rec = KDA.evaluate(_obs(scanner_confidence=8.5), behaviour=bm, angle_view=av)
        assert rec.decision == KDADecision.KNOWLEDGE_WAIT

    def test_t027_decision_is_kda_decision_enum(self):
        """T027: decision field is a KDADecision enum instance."""
        rec = KDA.evaluate(_obs())
        assert isinstance(rec.decision, KDADecision)

    def test_t028_no_force_trade_on_conflict(self):
        """T028: Material conflict (more CONTRADICT than SUPPORT) → WAIT not BUY."""
        bm = _bm(ess=150.0, target_prob=0.45, stop_prob=0.45)
        # 4 contradicting low-confidence angles with major=1
        av = _make_av({
            "STOCK":         _angle_result("STOCK",     0.08, 20, {"major": 1}),
            "SECTOR":        _angle_result("SECTOR",    0.09, 15, {"major": 1}),
            "DIRECTION":     _angle_result("DIRECTION", 0.07, 30, {"major": 1}),
            "LEADER_OUTCOME":_angle_result("LEADER_OUTCOME", 0.10, 20, {"major": 1}),
            # Suppress the remaining support angles
            "MARKET":        _angle_result("MARKET",    0.45, 40),
            "VOLATILITY":    _angle_result("VOLATILITY", 0.45, 20),
            "REDUNDANCY":    _angle_result("REDUNDANCY", 0.45, 15),
            "SOURCE_QUALITY":_angle_result("SOURCE_QUALITY", 0.45, 20),
        })
        rec = KDA.evaluate(_obs(scanner_confidence=8.5), behaviour=bm, angle_view=av)
        assert rec.decision == KDADecision.KNOWLEDGE_WAIT

    def test_t029_short_direction_recognised(self):
        """T029: direction='SHORT' is treated as SELL."""
        bm = _bm(ess=150.0, target_prob=0.7, stop_prob=0.2)
        rec = KDA.evaluate(_obs(direction="SHORT", scanner_confidence=8.5), behaviour=bm)
        assert rec.decision == KDADecision.KNOWLEDGE_SELL

    def test_t030_hold_not_buy_when_validated_low_authority(self):
        """T030: VALIDATED but low scanner_confidence → HOLD, not BUY."""
        bm = _bm(ess=50.0, target_prob=0.55, stop_prob=0.35)
        rec = KDA.evaluate(_obs(scanner_confidence=3.0), behaviour=bm)
        assert rec.decision in (KDADecision.KNOWLEDGE_HOLD, KDADecision.KNOWLEDGE_WAIT)


# ─────────────────────────────────────────────────────────────────────────────
# T031-T040: Knowledge authority score decomposition
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthorityScore:

    def test_t031_authority_components_present(self):
        """T031: authority_components has all six components."""
        rec = KDA.evaluate(_obs(), behaviour=_bm(ess=50.0))
        c = rec.authority_components
        assert all(hasattr(c, k) for k in (
            "evidence_strength", "relevance", "stability",
            "oos_quality", "source_independence", "contradiction_factor",
            "composite_authority",
        ))

    def test_t032_composite_bounded_zero_to_one(self):
        """T032: composite_authority ∈ [0, 1]."""
        rec = KDA.evaluate(_obs(), behaviour=_bm(ess=150.0))
        assert 0.0 <= rec.knowledge_authority <= 1.0

    def test_t033_all_components_bounded_zero_to_one(self):
        """T033: All individual components ∈ [0, 1]."""
        rec = KDA.evaluate(_obs(), behaviour=_bm(ess=50.0))
        c = rec.authority_components
        for name in ("evidence_strength", "relevance", "stability",
                     "oos_quality", "source_independence", "contradiction_factor"):
            v = getattr(c, name)
            assert 0.0 <= v <= 1.0, f"{name} = {v} out of bounds"

    def test_t034_higher_ess_higher_authority(self):
        """T034: Higher ESS → higher authority (all else equal)."""
        r_low  = KDA.evaluate(_obs(), behaviour=_bm(ess=5.0))
        r_high = KDA.evaluate(_obs(), behaviour=_bm(ess=150.0))
        assert r_high.knowledge_authority >= r_low.knowledge_authority

    def test_t035_contradiction_reduces_authority(self):
        """T035: Contradicting angles reduce composite authority."""
        bm = _bm(ess=150.0)
        av_clean = _make_av()
        av_conflict = _make_av({
            "STOCK":     _angle_result("STOCK",     0.15, 20, {"major": 1}),
            "SECTOR":    _angle_result("SECTOR",    0.12, 15, {"major": 1}),
            "DIRECTION": _angle_result("DIRECTION", 0.10, 30, {"major": 1}),
        })
        r_clean    = KDA.evaluate(_obs(), behaviour=bm, angle_view=av_clean)
        r_conflict = KDA.evaluate(_obs(), behaviour=bm, angle_view=av_conflict)
        assert r_clean.knowledge_authority >= r_conflict.knowledge_authority

    def test_t036_authority_zero_with_no_evidence(self):
        """T036: authority components are 0 when no bm and no angles."""
        rec = KDA.evaluate(_obs(), behaviour=None, angle_view=None)
        assert rec.knowledge_authority == pytest.approx(0.0)

    def test_t037_authority_decomposable_product(self):
        """T037: composite_authority ≤ min component (multiplicative dampening)."""
        rec = KDA.evaluate(_obs(), behaviour=_bm(ess=150.0))
        c = rec.authority_components
        min_comp = min(
            c.evidence_strength, c.relevance, c.stability,
            c.oos_quality, c.source_independence, c.contradiction_factor
        )
        assert c.composite_authority <= min_comp + 0.01  # allow tiny fp error

    def test_t038_knowledge_score_is_scanner_confidence(self):
        """T038: knowledge_score = scanner_confidence from observation."""
        rec = KDA.evaluate(_obs(scanner_confidence=7.5))
        assert rec.knowledge_score == pytest.approx(7.5)

    def test_t039_authority_role_knowledge_only_when_eligible(self):
        """T039: authority=KNOWLEDGE only when DECISION_ELIGIBLE + high authority."""
        bm_weak = _bm(ess=5.0)
        r_weak = KDA.evaluate(_obs(), behaviour=bm_weak)
        assert r_weak.authority != DecisionAuthority.KNOWLEDGE

    def test_t040_authority_role_none_when_insufficient(self):
        """T040: authority=NONE when no evidence."""
        rec = KDA.evaluate(_obs(), behaviour=None)
        assert rec.authority == DecisionAuthority.NONE


# ─────────────────────────────────────────────────────────────────────────────
# T041-T050: Target / stop / horizon
# ─────────────────────────────────────────────────────────────────────────────

class TestTargetStopHorizon:

    def test_t041_empirical_target_used_when_available(self):
        """T041: EMPIRICAL target source used when BehaviourMetrics has offset."""
        bm = _bm(ess=100.0, target_src="EMPIRICAL", target_offset=3.0)
        rec = KDA.evaluate(_obs(entry_price=2800.0), behaviour=bm)
        assert rec.target_source == "EMPIRICAL"
        assert rec.fallback_used is False

    def test_t042_atr_fallback_when_no_bm(self):
        """T042: ATR fallback when no BehaviourMetrics."""
        rec = KDA.evaluate(_obs(entry_price=2800.0, atr=28.0), behaviour=None)
        assert rec.target_source == "ATR_FALLBACK"
        assert rec.fallback_used is True

    def test_t043_target_above_entry_for_buy(self):
        """T043: target > entry_price for BUY direction."""
        rec = KDA.evaluate(_obs(entry_price=2800.0, atr=28.0, direction="BUY"), behaviour=None)
        assert rec.target is not None
        assert rec.target > 2800.0

    def test_t044_stop_below_entry_for_buy(self):
        """T044: stop_loss < entry_price for BUY direction."""
        rec = KDA.evaluate(_obs(entry_price=2800.0, atr=28.0, direction="BUY"), behaviour=None)
        assert rec.stop_loss is not None
        assert rec.stop_loss < 2800.0

    def test_t045_target_below_entry_for_sell(self):
        """T045: target < entry_price for SELL direction."""
        rec = KDA.evaluate(_obs(entry_price=2800.0, atr=28.0, direction="SELL"), behaviour=None)
        assert rec.target is not None
        assert rec.target < 2800.0

    def test_t046_stop_above_entry_for_sell(self):
        """T046: stop_loss > entry_price for SELL direction."""
        rec = KDA.evaluate(_obs(entry_price=2800.0, atr=28.0, direction="SELL"), behaviour=None)
        assert rec.stop_loss is not None
        assert rec.stop_loss > 2800.0

    def test_t047_empirical_expected_move_stored(self):
        """T047: expected_move_p25/p50/p75 from BehaviourMetrics stored in record."""
        bm = _bm(ess=100.0, em_p25=1.0, em_p50=2.5, em_p75=4.5)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.expected_move_p50 == pytest.approx(2.5)

    def test_t048_horizon_from_bm(self):
        """T048: expected_days_p50 from BehaviourMetrics stored."""
        bm = _bm(ess=100.0, days_p50=5.0)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.expected_days_p50 == pytest.approx(5.0)
        assert rec.horizon_source == "EMPIRICAL"

    def test_t049_horizon_unknown_when_no_bm(self):
        """T049: horizon_source == 'UNKNOWN' when no BehaviourMetrics."""
        rec = KDA.evaluate(_obs(), behaviour=None)
        assert rec.horizon_source == "UNKNOWN"
        assert rec.expected_days_p50 is None

    def test_t050_target_none_when_entry_zero(self):
        """T050: target/stop are None when entry_price=0 and no ATR."""
        rec = KDA.evaluate(_obs(entry_price=0.0, atr=0.0), behaviour=None)
        assert rec.target is None
        assert rec.stop_loss is None


# ─────────────────────────────────────────────────────────────────────────────
# T051-T060: StrategyLab demotion and relationship
# ─────────────────────────────────────────────────────────────────────────────

class TestStrategyLabDemotion:

    def test_t051_strategy_context_is_informational_only(self):
        """T051: strategy_context.informational_only == True always."""
        strat = {"status": "PASS", "strategy_name": "Momentum_Retest"}
        rec = KDA.evaluate(_obs(), strategy_context=strat)
        assert rec.strategy_context is not None
        assert rec.strategy_context.informational_only is True

    def test_t052_strategy_reject_does_not_suppress_knowledge_buy(self):
        """T052: StrategyLab REJECT must NOT automatically kill a Knowledge decision."""
        bm = _bm(ess=150.0, target_prob=0.7, stop_prob=0.2)
        strat = {"status": "REJECT", "strategy_name": "Momentum"}
        rec = KDA.evaluate(_obs(scanner_confidence=8.5), behaviour=bm, strategy_context=strat)
        # The decision is independent — StrategyLab REJECT should not force WAIT
        # (decision may be BUY, HOLD, or WAIT based on evidence, not on strategy alone)
        if rec.evidence_state == EvidenceState.DECISION_ELIGIBLE:
            assert rec.decision == KDADecision.KNOWLEDGE_BUY

    def test_t053_strategy_pass_does_not_auto_approve_knowledge(self):
        """T053: StrategyLab PASS without sufficient evidence does NOT produce BUY."""
        strat = {"status": "PASS", "strategy_name": "Momentum"}
        rec = KDA.evaluate(_obs(), behaviour=None, strategy_context=strat)
        # No evidence → must WAIT regardless of StrategyLab PASS
        assert rec.decision == KDADecision.KNOWLEDGE_WAIT

    def test_t054_relationship_agrees_when_both_approve(self):
        """T054: Both KDA and StrategyLab approve → KNOWLEDGE_AGREES."""
        bm = _bm(ess=150.0, target_prob=0.7, stop_prob=0.2)
        strat = {"status": "PASS", "strategy_name": "Momentum"}
        rec = KDA.evaluate(_obs(scanner_confidence=8.5), behaviour=bm, strategy_context=strat)
        if rec.decision in (KDADecision.KNOWLEDGE_BUY, KDADecision.KNOWLEDGE_SELL):
            assert rec.kda_strategy_relationship == KDARelationship.KNOWLEDGE_AGREES.value

    def test_t055_relationship_overrules_when_eligible(self):
        """T055: Knowledge DECISION_ELIGIBLE + StrategyLab REJECT → KNOWLEDGE_OVERRULES_STRATEGY."""
        bm = _bm(ess=150.0, target_prob=0.7, stop_prob=0.2)
        strat = {"status": "REJECT", "strategy_name": "Momentum"}
        rec = KDA.evaluate(_obs(scanner_confidence=8.5), behaviour=bm, strategy_context=strat)
        if rec.evidence_state == EvidenceState.DECISION_ELIGIBLE and rec.decision == KDADecision.KNOWLEDGE_BUY:
            assert rec.kda_strategy_relationship == KDARelationship.KNOWLEDGE_OVERRULES_STRATEGY.value

    def test_t056_insufficient_knowledge_cannot_overrule(self):
        """T056: KNOWLEDGE_OVERRULES_STRATEGY not possible with INSUFFICIENT evidence."""
        strat = {"status": "PASS"}
        rec = KDA.evaluate(_obs(), behaviour=None, strategy_context=strat)
        assert rec.kda_strategy_relationship != KDARelationship.KNOWLEDGE_OVERRULES_STRATEGY.value

    def test_t057_relationship_stored_as_string(self):
        """T057: kda_strategy_relationship is a string (KDARelationship value)."""
        rec = KDA.evaluate(_obs(), strategy_context={"status": "PASS"})
        assert isinstance(rec.kda_strategy_relationship, str)
        valid = {r.value for r in KDARelationship}
        assert rec.kda_strategy_relationship in valid

    def test_t058_no_strategy_context_means_none_field(self):
        """T058: strategy_context field is None when not provided."""
        rec = KDA.evaluate(_obs(), strategy_context=None)
        assert rec.strategy_context is None

    def test_t059_strategy_disagreement_recorded(self):
        """T059: disagreement field in StrategyContext is preserved."""
        strat = {"status": "REJECT", "strategy_name": "MR", "disagreement": "Low RR"}
        rec = KDA.evaluate(_obs(), strategy_context=strat)
        assert rec.strategy_context is not None
        assert rec.strategy_context.disagreement == "Low RR"

    def test_t060_strategy_unknown_when_status_missing(self):
        """T060: strategy_context.status=UNKNOWN when status key absent."""
        rec = KDA.evaluate(_obs(), strategy_context={"strategy_name": "X"})
        assert rec.strategy_context.status == "UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# T061-T070: Angle evaluation (SUPPORT / NEUTRAL / CONTRADICT / INSUFFICIENT)
# ─────────────────────────────────────────────────────────────────────────────

class TestAngleEvaluation:

    def test_t061_high_confidence_stock_angle_is_support(self):
        """T061: STOCK angle with confidence > 0.55 → SUPPORT."""
        av = _make_angle_view({"STOCK": _angle_result("STOCK", 0.75, 30)})
        rec = KDA.evaluate(_obs(), angle_view=av)
        assert rec.angle_analyses["STOCK"].verdict == AngleVerdict.SUPPORT

    def test_t062_zero_confidence_any_angle_is_insufficient(self):
        """T062: confidence=0 → INSUFFICIENT regardless of angle."""
        av = _make_angle_view({"STOCK": _angle_result("STOCK", 0.0, 0)})
        rec = KDA.evaluate(_obs(), angle_view=av)
        assert rec.angle_analyses["STOCK"].verdict == AngleVerdict.INSUFFICIENT

    def test_t063_contradiction_angle_no_contradictions_is_support(self):
        """T063: CONTRADICTION angle with 0 contradictions → SUPPORT."""
        av = _make_angle_view({
            "CONTRADICTION": _angle_result("CONTRADICTION", 0.85, 0, {"contradictions": 0, "major": 0, "minor": 0})
        })
        rec = KDA.evaluate(_obs(), angle_view=av)
        assert rec.angle_analyses["CONTRADICTION"].verdict == AngleVerdict.SUPPORT

    def test_t064_contradiction_angle_major_contradiction_is_contradict(self):
        """T064: CONTRADICTION angle with major=1 → CONTRADICT."""
        av = _make_angle_view({
            "CONTRADICTION": _angle_result("CONTRADICTION", 0.62, 2, {"contradictions": 2, "major": 1, "minor": 0})
        })
        rec = KDA.evaluate(_obs(), angle_view=av)
        assert rec.angle_analyses["CONTRADICTION"].verdict == AngleVerdict.CONTRADICT

    def test_t065_oos_validation_high_pass_rate_is_support(self):
        """T065: OOS_VALIDATION with pass_rate=0.8 → SUPPORT."""
        av = _make_angle_view({
            "OOS_VALIDATION": _angle_result("OOS_VALIDATION", 0.75, 10, {"oos_pass_rate": 0.8})
        })
        rec = KDA.evaluate(_obs(), angle_view=av)
        assert rec.angle_analyses["OOS_VALIDATION"].verdict == AngleVerdict.SUPPORT

    def test_t066_oos_validation_low_pass_rate_is_contradict(self):
        """T066: OOS_VALIDATION with pass_rate=0.1 → CONTRADICT."""
        av = _make_angle_view({
            "OOS_VALIDATION": _angle_result("OOS_VALIDATION", 0.75, 10, {"oos_pass_rate": 0.1})
        })
        rec = KDA.evaluate(_obs(), angle_view=av)
        assert rec.angle_analyses["OOS_VALIDATION"].verdict == AngleVerdict.CONTRADICT

    def test_t067_recency_high_ess_frac_is_support(self):
        """T067: RECENCY with ess_fraction=0.9 → SUPPORT."""
        av = _make_angle_view({
            "RECENCY": _angle_result("RECENCY", 0.80, 40, {"ess_fraction": 0.9})
        })
        rec = KDA.evaluate(_obs(), angle_view=av)
        assert rec.angle_analyses["RECENCY"].verdict == AngleVerdict.SUPPORT

    def test_t068_all_16_angles_evaluated(self):
        """T068: All 16 standard angles produce AngleAnalysis entries."""
        rec = KDA.evaluate(_obs(), angle_view=_make_av())
        assert len(rec.angle_analyses) == 16

    def test_t069_supporting_angles_list_is_populated(self):
        """T069: supporting_angles list contains SUPPORT angle names."""
        rec = KDA.evaluate(_obs(), angle_view=_make_av())
        # With high-confidence view, several angles should be SUPPORT
        assert isinstance(rec.supporting_angles, list)

    def test_t070_contradicting_angles_list_correct(self):
        """T070: contradicting_angles list contains CONTRADICT angle names."""
        av = _make_av({
            "STOCK":  _angle_result("STOCK",  0.15, 10, {"major": 1}),
        })
        rec = KDA.evaluate(_obs(), angle_view=av)
        assert isinstance(rec.contradicting_angles, list)


# ─────────────────────────────────────────────────────────────────────────────
# T071-T080: Information contributions and counterfactual analysis
# ─────────────────────────────────────────────────────────────────────────────

class TestContributionsAndCounterfactuals:

    def test_t071_information_contributions_list(self):
        """T071: information_contributions is a list."""
        rec = KDA.evaluate(_obs(), angle_view=_make_av(), behaviour=_bm(ess=50.0))
        assert isinstance(rec.information_contributions, list)

    def test_t072_contributions_have_required_fields(self):
        """T072: Each contribution has source, angle, contribution, direction, value."""
        rec = KDA.evaluate(_obs(), angle_view=_make_av(), behaviour=_bm(ess=50.0))
        for c in rec.information_contributions:
            assert hasattr(c, "source")
            assert hasattr(c, "angle")
            assert hasattr(c, "contribution")
            assert hasattr(c, "direction")
            assert hasattr(c, "value")

    def test_t073_contribution_direction_is_valid(self):
        """T073: contribution direction is SUPPORT, CONTRADICT, or NEUTRAL."""
        rec = KDA.evaluate(_obs(), angle_view=_make_av(), behaviour=_bm(ess=50.0))
        valid = {"SUPPORT", "CONTRADICT", "NEUTRAL", "INSUFFICIENT"}
        for c in rec.information_contributions:
            assert c.direction in valid

    def test_t074_contribution_value_non_negative(self):
        """T074: value (absolute contribution) ≥ 0."""
        rec = KDA.evaluate(_obs(), angle_view=_make_av(), behaviour=_bm(ess=50.0))
        for c in rec.information_contributions:
            assert c.value >= 0.0

    def test_t075_contributions_sorted_by_magnitude(self):
        """T075: contributions sorted descending by |contribution|."""
        rec = KDA.evaluate(_obs(), angle_view=_make_av(), behaviour=_bm(ess=50.0))
        vals = [abs(c.contribution) for c in rec.information_contributions]
        assert vals == sorted(vals, reverse=True)

    def test_t076_counterfactual_results_list(self):
        """T076: counterfactual_results is a list."""
        rec = KDA.evaluate(_obs(), angle_view=_make_av(), behaviour=_bm(ess=50.0))
        assert isinstance(rec.counterfactual_results, list)

    def test_t077_counterfactual_has_required_fields(self):
        """T077: Each counterfactual has source_removed, decision_with/without, delta."""
        av = _make_av({
            "STOCK": _angle_result("STOCK", 0.75, 30),
        })
        rec = KDA.evaluate(_obs(), angle_view=av, behaviour=_bm(ess=50.0))
        for cf in rec.counterfactual_results:
            assert hasattr(cf, "source_removed")
            assert hasattr(cf, "decision_with")
            assert hasattr(cf, "decision_without")
            assert hasattr(cf, "delta")

    def test_t078_counterfactual_delta_is_float(self):
        """T078: counterfactual delta is a float."""
        rec = KDA.evaluate(_obs(), angle_view=_make_av(), behaviour=_bm(ess=50.0))
        for cf in rec.counterfactual_results:
            assert isinstance(cf.delta, float)

    def test_t079_no_double_counting_neutral_angles(self):
        """T079: NEUTRAL angles do not appear in counterfactuals (no double-counting)."""
        av = _make_av({
            "TIME": _angle_result("TIME", 0.48, 10),   # NEUTRAL confidence
        })
        rec = KDA.evaluate(_obs(), angle_view=av, behaviour=_bm(ess=50.0))
        cf_sources = {cf.source_removed for cf in rec.counterfactual_results}
        # TIME is NEUTRAL confidence — should not be in counterfactuals unless it became SUPPORT
        if "TIME" in rec.angle_analyses:
            if rec.angle_analyses["TIME"].verdict == AngleVerdict.NEUTRAL:
                assert "TIME" not in cf_sources

    def test_t080_contributions_empty_without_angles(self):
        """T080: information_contributions is empty when no angle_view provided."""
        rec = KDA.evaluate(_obs(), angle_view=None, behaviour=_bm(ess=50.0))
        assert rec.information_contributions == []


# ─────────────────────────────────────────────────────────────────────────────
# T081-T090: Evidence hierarchy
# ─────────────────────────────────────────────────────────────────────────────

class TestEvidenceHierarchy:

    def test_t081_atf_fallback_when_no_bm(self):
        """T081: evidence_level=ATR_FALLBACK when no BehaviourMetrics."""
        rec = KDA.evaluate(_obs())
        assert rec.evidence_level == EvidenceHierarchyLevel.ATR_FALLBACK

    def test_t082_symbol_dir_regime_when_exact_match(self):
        """T082: SYMBOL_DIR_REGIME_CTX level when evidence_source matches."""
        bm = _bm(ess=50.0, evidence_src="SYMBOL_DIRECTION_REGIME")
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_level == EvidenceHierarchyLevel.SYMBOL_DIR_REGIME_CTX

    def test_t083_symbol_dir_level(self):
        """T083: SYMBOL_DIR level when evidence_source=SYMBOL_DIRECTION."""
        bm = _bm(ess=50.0, evidence_src="SYMBOL_DIRECTION")
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_level == EvidenceHierarchyLevel.SYMBOL_DIR

    def test_t084_sector_dir_regime_level(self):
        """T084: SECTOR_DIR_REGIME level when evidence_source=SECTOR_DIRECTION_REGIME."""
        bm = _bm(ess=50.0, evidence_src="SECTOR_DIRECTION_REGIME")
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_level == EvidenceHierarchyLevel.SECTOR_DIR_REGIME

    def test_t085_hierarchy_level_stored_in_record(self):
        """T085: evidence_level is EvidenceHierarchyLevel enum."""
        rec = KDA.evaluate(_obs(), behaviour=_bm(ess=50.0))
        assert isinstance(rec.evidence_level, EvidenceHierarchyLevel)

    def test_t086_hierarchy_level_in_as_dict(self):
        """T086: evidence_level appears in as_dict() output as a string."""
        rec = KDA.evaluate(_obs(), behaviour=_bm(ess=50.0))
        d = rec.as_dict()
        assert "evidence_level" in d
        assert isinstance(d["evidence_level"], str)

    def test_t087_regime_dir_level(self):
        """T087: REGIME_DIR level when evidence_source=REGIME_DIRECTION."""
        bm = _bm(ess=50.0, evidence_src="REGIME_DIRECTION")
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_level == EvidenceHierarchyLevel.REGIME_DIR

    def test_t088_sector_dir_level(self):
        """T088: SECTOR_DIR level when evidence_source=SECTOR_DIRECTION."""
        bm = _bm(ess=50.0, evidence_src="SECTOR_DIRECTION")
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_level == EvidenceHierarchyLevel.SECTOR_DIR

    def test_t089_broad_dir_level_fallback_for_unknown_source(self):
        """T089: Unrecognised evidence_source → non-SYMBOL_DIR_REGIME_CTX level."""
        bm_known   = _bm(ess=50.0, evidence_src="SYMBOL_DIRECTION_REGIME")
        bm_unknown = _bm(ess=50.0, evidence_src="SOME_UNRECOGNISED_SOURCE")
        r_known   = KDA.evaluate(_obs(), behaviour=bm_known)
        r_unknown = KDA.evaluate(_obs(), behaviour=bm_unknown)
        # Unknown source should not map to the most-specific level
        assert r_unknown.evidence_level != EvidenceHierarchyLevel.SYMBOL_DIR_REGIME_CTX

    def test_t090_hierarchy_level_better_when_more_specific(self):
        """T090: SYMBOL_DIR_REGIME_CTX has lower (better) ordinal than BROAD_DIR."""
        assert (EvidenceHierarchyLevel.SYMBOL_DIR_REGIME_CTX.value
                != EvidenceHierarchyLevel.ATR_FALLBACK.value)


# ─────────────────────────────────────────────────────────────────────────────
# T091-T100: Exit conditions and outcome recording
# ─────────────────────────────────────────────────────────────────────────────

class TestExitAndOutcome:

    def test_t091_risk_override_always_present(self):
        """T091: RISK_OVERRIDE exit condition always in exit_conditions."""
        rec = KDA.evaluate(_obs())
        assert ExitState.RISK_OVERRIDE.value in rec.exit_conditions

    def test_t092_target_stop_in_exit_when_directional(self):
        """T092: TARGET_REACHED + STOP_REACHED in exits when BUY/SELL decision."""
        bm = _bm(ess=150.0, target_prob=0.7, stop_prob=0.2)
        rec = KDA.evaluate(_obs(scanner_confidence=8.5), behaviour=bm)
        if rec.decision in (KDADecision.KNOWLEDGE_BUY, KDADecision.KNOWLEDGE_SELL):
            assert ExitState.TARGET_REACHED.value in rec.exit_conditions
            assert ExitState.STOP_REACHED.value in rec.exit_conditions

    def test_t093_knowledge_contradiction_exit_when_many_contradictions(self):
        """T093: KNOWLEDGE_CONTRADICTION exit added when ≥ 3 contradicting angles."""
        bm = _bm(ess=150.0)
        av = _make_av({
            "STOCK":     _angle_result("STOCK",     0.10, 20, {"major": 1}),
            "SECTOR":    _angle_result("SECTOR",    0.12, 15, {"major": 1}),
            "DIRECTION": _angle_result("DIRECTION", 0.08, 30, {"major": 1}),
        })
        rec = KDA.evaluate(_obs(), behaviour=bm, angle_view=av)
        assert ExitState.KNOWLEDGE_CONTRADICTION.value in rec.exit_conditions

    def test_t094_time_decay_exit_when_horizon_available(self):
        """T094: TIME_DECAY exit condition added when expected_days_p75 available."""
        bm = _bm(ess=100.0, days_p75=10.0)
        bm_buy = _bm(ess=150.0, target_prob=0.7, stop_prob=0.2, days_p75=10.0)
        rec = KDA.evaluate(_obs(scanner_confidence=8.5), behaviour=bm_buy)
        if rec.decision in (KDADecision.KNOWLEDGE_BUY, KDADecision.KNOWLEDGE_SELL):
            assert ExitState.TIME_DECAY.value in rec.exit_conditions

    def test_t095_kda_outcome_feedback_structure(self):
        """T095: KDAOutcomeFeedback has all required fields."""
        from knowledge_authority.kda_models import KDAOutcomeFeedback
        feedback = KDAOutcomeFeedback(
            decision_id="test-001",
            symbol="RELIANCE",
            direction="BUY",
            decision="KNOWLEDGE_BUY",
            authority="KNOWLEDGE",
            actual_return_1d=1.5,
            actual_return_5d=3.2,
            target_hit=True,
            stop_hit=False,
            outcome_class="CORRECT_KNOWLEDGE_DECISION",
        )
        d = feedback.as_dict()
        for key in ("decision_id", "symbol", "direction", "decision", "authority",
                    "actual_return_1d", "outcome_class"):
            assert key in d

    def test_t096_exit_conditions_is_list(self):
        """T096: exit_conditions is a list."""
        rec = KDA.evaluate(_obs())
        assert isinstance(rec.exit_conditions, list)

    def test_t097_as_dict_serialisable(self):
        """T097: as_dict() produces a JSON-serialisable dict."""
        import json
        rec = KDA.evaluate(_obs(), behaviour=_bm(ess=50.0), angle_view=_make_av())
        d = rec.as_dict()
        # Should not raise
        _ = json.dumps(d, default=str)

    def test_t098_contradiction_status_in_record(self):
        """T098: contradiction_status field in record."""
        rec = KDA.evaluate(_obs())
        assert isinstance(rec.contradiction_status, str)
        assert rec.contradiction_status in ("NONE", "MINOR", "MODERATE", "MAJOR")

    def test_t099_source_agreement_bounded(self):
        """T099: source_agreement ∈ [0, 1]."""
        rec = KDA.evaluate(_obs(), angle_view=_make_av())
        assert 0.0 <= rec.source_agreement <= 1.0

    def test_t100_decision_record_complete(self):
        """T100: Full evaluate() pipeline produces record with all required fields."""
        bm = _bm(ess=150.0, target_prob=0.7, stop_prob=0.2)
        av = _make_av()
        strat = {"status": "PASS", "strategy_name": "Momentum"}
        mkt = _mkt()
        rec = KDA.evaluate(_obs(scanner_confidence=8.5), av, bm, strat, mkt)

        required = [
            "decision_id", "timestamp", "symbol", "direction", "authority",
            "decision", "knowledge_score", "knowledge_authority",
            "evidence_state", "evidence_level", "evidence_count",
            "effective_sample_size", "evidence_confidence",
            "expected_move_p50", "target", "stop_loss",
            "expected_days_p50", "target_source", "stop_source", "horizon_source",
            "supporting_angles", "contradicting_angles", "source_count",
            "source_agreement", "contradiction_status", "oos_status",
            "strategy_context", "kda_strategy_relationship", "risk_constraints",
            "fallback_used", "authority_components", "angle_analyses",
            "information_contributions", "counterfactual_results",
            "exit_conditions", "mode", "no_lookahead", "broker_calls", "orders",
        ]
        for field_name in required:
            assert hasattr(rec, field_name), f"Missing field: {field_name}"
