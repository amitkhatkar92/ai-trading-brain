"""
DTA-DEBATE-AUTHORITY-002C — TechnicalAnalyst structural validator tests.

Calls the real MultiAgentDebate._technical_vote() (via .run()) and the real
DecisionEngine.decide() directly (production code, not a simulation) to verify:

  1. Directional geometry: inverted/malformed BUY and SELL/SHORT trades are
     STRUCTURAL_INVALID (vote="reject").
  2. Valid geometry + sane ATR ratio -> STRUCTURALLY_SOUND (vote="approve").
  3. ATR ratio outside [TA_ATR_RATIO_MIN, TA_ATR_RATIO_MAX] -> STRUCTURALLY_WEAK
     (vote="reduce_size"), only when atr > 0.
  4. Missing ATR (atr == 0) -> neutral on that dimension, never a penalty.
  5. ATR_FALLBACK provenance -> secondary WEAK indicator, never invalidates
     alone.
  6. No stacking: multiple weak conditions still produce exactly one
     reduce_size tier (score=5.0), not a compounded penalty.
  7. KDA confidence 0 vs 10 identity: confidence must not affect the vote at
     all (strongest ownership test).
  8. strategy_name / authorization_source independence.
  9. STRUCTURAL_INVALID actually triggers DecisionEngine's existing
     hard-reject path end-to-end (not just checked in isolation).
"""
from __future__ import annotations

from datetime import datetime

from debate_system.multi_agent_debate import MultiAgentDebate, TA_ATR_RATIO_MIN, TA_ATR_RATIO_MAX
from decision_ai.decision_engine import DecisionEngine
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        timestamp=datetime.now(), indices={},
        regime=RegimeLabel.RANGE_MARKET, volatility=VolatilityLevel.MEDIUM,
        vix=15.0, pcr=1.0, market_breadth=0.5,
    )


def _sig(**overrides) -> TradeSignal:
    defaults = dict(
        symbol="TESTSTOCK",
        direction=SignalDirection.BUY,
        signal_type=SignalType.EQUITY,
        entry_price=100.0,
        stop_loss=95.0,
        target_price=110.0,
        confidence=6.0,
        strategy_name="unassigned",
        atr=5.0,   # sane: stop_distance=5, ratio=1.0, within [0.5,4.0]
    )
    defaults.update(overrides)
    return TradeSignal(**defaults)


def _technical_vote_of(sig: TradeSignal):
    votes = MultiAgentDebate().run(sig, _snapshot())
    return next(v for v in votes if v.agent_name == "TechnicalAnalystAI")


# ─────────────────────────────────────────────────────────────
# 1-2. Directional geometry
# ─────────────────────────────────────────────────────────────

def test_valid_buy_geometry_is_approved():
    v = _technical_vote_of(_sig(direction=SignalDirection.BUY,
                                entry_price=100.0, stop_loss=95.0, target_price=110.0))
    assert v.vote == "approve"
    assert v.score == 8.0


def test_inverted_buy_geometry_is_structurally_invalid():
    # stop above entry for a BUY — malformed
    v = _technical_vote_of(_sig(direction=SignalDirection.BUY,
                                entry_price=100.0, stop_loss=105.0, target_price=110.0))
    assert v.vote == "reject"
    assert v.score == 3.0
    assert v.suggested_position_modifier == 0.0


def test_buy_target_below_entry_is_structurally_invalid():
    v = _technical_vote_of(_sig(direction=SignalDirection.BUY,
                                entry_price=100.0, stop_loss=95.0, target_price=98.0))
    assert v.vote == "reject"


def test_valid_short_geometry_is_approved():
    v = _technical_vote_of(_sig(direction=SignalDirection.SHORT,
                                entry_price=100.0, stop_loss=105.0, target_price=90.0))
    assert v.vote == "approve"
    assert v.score == 8.0


def test_inverted_short_geometry_is_structurally_invalid():
    # stop below entry for a SHORT — malformed
    v = _technical_vote_of(_sig(direction=SignalDirection.SHORT,
                                entry_price=100.0, stop_loss=95.0, target_price=90.0))
    assert v.vote == "reject"


def test_equality_geometry_is_invalid_not_valid():
    # stop == entry for a BUY — equality must be treated as invalid
    v = _technical_vote_of(_sig(direction=SignalDirection.BUY,
                                entry_price=100.0, stop_loss=100.0, target_price=110.0))
    assert v.vote == "reject"


# ─────────────────────────────────────────────────────────────
# 3-4. ATR-vs-stop-distance sanity
# ─────────────────────────────────────────────────────────────

def test_atr_ratio_too_tight_is_structurally_weak():
    # stop_distance=5, atr=20 -> ratio=0.25 < TA_ATR_RATIO_MIN
    v = _technical_vote_of(_sig(atr=20.0))
    assert v.vote == "reduce_size"
    assert v.score == 5.0
    assert v.suggested_position_modifier == 0.7


def test_atr_ratio_too_wide_is_structurally_weak():
    # stop_distance=5, atr=1 -> ratio=5.0 > TA_ATR_RATIO_MAX
    v = _technical_vote_of(_sig(atr=1.0))
    assert v.vote == "reduce_size"
    assert v.score == 5.0


def test_atr_ratio_boundary_values_stay_sound():
    # ratio exactly at MIN/MAX bounds should not be flagged (only outside is weak)
    v_min = _technical_vote_of(_sig(atr=5.0 / TA_ATR_RATIO_MIN))   # ratio == MIN
    v_max = _technical_vote_of(_sig(atr=5.0 / TA_ATR_RATIO_MAX))   # ratio == MAX
    assert v_min.vote == "approve"
    assert v_max.vote == "approve"


def test_missing_atr_is_neutral_not_penalized():
    v = _technical_vote_of(_sig(atr=0.0))
    assert v.vote == "approve"
    assert v.score == 8.0


# ─────────────────────────────────────────────────────────────
# 5. Provenance — secondary indicator only
# ─────────────────────────────────────────────────────────────

def test_atr_fallback_provenance_is_weak_but_not_invalid():
    v = _technical_vote_of(_sig(target_source="ATR_FALLBACK", stop_source="ATR_FALLBACK"))
    assert v.vote == "reduce_size"
    assert v.score == 5.0


def test_kda_empirical_provenance_with_sane_atr_is_sound():
    v = _technical_vote_of(_sig(target_source="KDA_EMPIRICAL", stop_source="KDA_EMPIRICAL"))
    assert v.vote == "approve"
    assert v.score == 8.0


# ─────────────────────────────────────────────────────────────
# 6. No stacking of weak conditions
# ─────────────────────────────────────────────────────────────

def test_multiple_weak_conditions_do_not_stack():
    # Both ATR-ratio-too-tight AND ATR_FALLBACK provenance present simultaneously
    v = _technical_vote_of(_sig(atr=20.0, target_source="ATR_FALLBACK", stop_source="ATR_FALLBACK"))
    assert v.vote == "reduce_size"
    assert v.score == 5.0                       # still exactly one weak tier
    assert v.suggested_position_modifier == 0.7  # not further reduced
    assert "ATR ratio" in v.reasoning and "ATR_FALLBACK" in v.reasoning


# ─────────────────────────────────────────────────────────────
# 7. KDA confidence 0 vs 10 identity (strongest ownership test)
# ─────────────────────────────────────────────────────────────

def test_confidence_0_and_10_produce_identical_technical_vote():
    common = dict(
        entry_price=100.0, stop_loss=95.0, target_price=110.0, atr=5.0,
        strategy_name="KDA_AUTHORITY",
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED", kda_conviction=8.0,
    )
    v_low  = _technical_vote_of(_sig(confidence=0.0,  **common))
    v_high = _technical_vote_of(_sig(confidence=10.0, **common))

    assert v_low.vote == v_high.vote
    assert v_low.score == v_high.score
    assert v_low.suggested_position_modifier == v_high.suggested_position_modifier
    assert v_low.reasoning == v_high.reasoning


# ─────────────────────────────────────────────────────────────
# 8. strategy_name / authorization_source independence
# ─────────────────────────────────────────────────────────────

def test_strategy_name_and_authorization_source_do_not_affect_vote():
    common = dict(entry_price=100.0, stop_loss=95.0, target_price=110.0, atr=5.0, confidence=6.0)
    v_named = _technical_vote_of(_sig(strategy_name="Mean_Reversion",
                                       authorization_source=None, **common))
    v_kda   = _technical_vote_of(_sig(strategy_name="KDA_AUTHORITY",
                                       authorization_source="KDA",
                                       kda_decision="KNOWLEDGE_BUY",
                                       kda_evidence_state="VALIDATED", **common))
    assert v_named.vote == v_kda.vote
    assert v_named.score == v_kda.score
    assert v_named.suggested_position_modifier == v_kda.suggested_position_modifier


# ─────────────────────────────────────────────────────────────
# 9. STRUCTURAL_INVALID actually triggers DecisionEngine's hard-reject path
# ─────────────────────────────────────────────────────────────

def test_structural_invalid_triggers_decision_engine_hard_reject():
    sig = _sig(direction=SignalDirection.BUY,
               entry_price=100.0, stop_loss=105.0, target_price=110.0)  # inverted stop
    snapshot = _snapshot()
    votes = MultiAgentDebate().run(sig, snapshot)
    result = DecisionEngine().decide(sig, votes, snapshot)

    assert result.approved is False
    assert result.confidence_score == 0.0
    assert result.position_size_modifier == 0.0
    assert "Hard reject" in result.reasoning


def test_structurally_sound_signal_still_reaches_normal_decision_tiering():
    sig = _sig(direction=SignalDirection.BUY,
               entry_price=100.0, stop_loss=95.0, target_price=110.0, atr=5.0)
    snapshot = _snapshot()
    votes = MultiAgentDebate().run(sig, snapshot)
    result = DecisionEngine().decide(sig, votes, snapshot)

    # Not vetoed by TechnicalAnalyst; whatever tiering results comes from the
    # normal weighted-average path, not a hard reject.
    assert "Hard reject" not in result.reasoning
