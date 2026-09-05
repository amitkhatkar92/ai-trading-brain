"""
DTA-DEBATE-AUTHORITY-003 — RegimeDebateAI canonical KDA-authority gate tests.

Calls the real MultiAgentDebate().run() (via the real _regime_vote()) directly
(production code, not a simulation) to verify:

  1. DTA-KDA-AUTHORITY-WIDEN-001: weak-evidence (USEFUL) KDA-authorized
     signal IS now exempted -> score=8.0/approve/modifier=1.0, same as
     VALIDATED/DECISION_ELIGIBLE -- evidence_state no longer gates authority.
  2. "BOTH"-authorized, VALIDATED evidence, original StrategyLab strategy_name
     retained -> IS exempted -> score=8.0/approve/modifier=1.0 regardless of
     regime (false negative fixed).
  3. Genuine KDA-only, DECISION_ELIGIBLE, strategy_name="KDA_AUTHORITY" ->
     still exempted -> score=8.0 (no regression).
  4. Ordinary StrategyLab-only signal, no KDA fields -> regime-matrix
     behavior unchanged.
  5. KDA confidence 0-vs-10 identity test.
  6. strategy_name-independence test for the qualifying population.
  7. Partial-match test (authorization_source="STRATEGY_LAB" despite
     KNOWLEDGE_BUY + VALIDATED) -> NOT exempted (conjunctive, not disjunctive).
"""
from __future__ import annotations

from datetime import datetime

from debate_system.multi_agent_debate import MultiAgentDebate
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel


def _snapshot(regime=RegimeLabel.RANGE_MARKET) -> MarketSnapshot:
    return MarketSnapshot(
        timestamp=datetime.now(), indices={},
        regime=regime, volatility=VolatilityLevel.MEDIUM,
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
    )
    defaults.update(overrides)
    return TradeSignal(**defaults)


def _regime_vote_of(sig: TradeSignal, regime=RegimeLabel.RANGE_MARKET):
    votes = MultiAgentDebate().run(sig, _snapshot(regime))
    return next(v for v in votes if v.agent_name == "RegimeDebateAI")


def test_weak_evidence_kda_authority_label_now_exempted():
    """DTA-KDA-AUTHORITY-WIDEN-001: USEFUL evidence + KNOWLEDGE_BUY +
    authorization_source KDA is now exempted, same as VALIDATED/
    DECISION_ELIGIBLE."""
    sig = _sig(strategy_name="KDA_AUTHORITY", confidence=8.0,
               kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
               kda_evidence_state="USEFUL")
    v = _regime_vote_of(sig, regime=RegimeLabel.RANGE_MARKET)
    assert v.vote == "approve"
    assert v.score == 8.0


def test_both_authorized_validated_original_strategy_name_is_exempted():
    sig = _sig(strategy_name="Momentum_Retest", confidence=6.0,
               kda_decision="KNOWLEDGE_BUY", authorization_source="BOTH",
               kda_evidence_state="VALIDATED")
    # Use a regime where "Momentum_Retest" is NOT even relevant, to prove the
    # exemption is not coincidentally matching the matrix.
    v = _regime_vote_of(sig, regime=RegimeLabel.BEAR_MARKET)
    assert v.vote == "approve"
    assert v.score == 8.0
    assert v.suggested_position_modifier == 1.0


def test_kda_only_decision_eligible_still_exempted():
    sig = _sig(strategy_name="KDA_AUTHORITY", confidence=7.6,
               kda_decision="KNOWLEDGE_SELL", authorization_source="KDA",
               kda_evidence_state="DECISION_ELIGIBLE")
    v = _regime_vote_of(sig)
    assert v.vote == "approve"
    assert v.score == 8.0


def test_ordinary_strategylab_signal_matrix_behavior_unchanged():
    sig_match = _sig(strategy_name="Momentum_Retest", confidence=6.0)
    v_match = _regime_vote_of(sig_match, regime=RegimeLabel.BULL_TREND)
    assert v_match.vote == "approve"
    assert v_match.score == 8.0

    sig_nomatch = _sig(strategy_name="Equity_Breakout", confidence=6.0)
    v_nomatch = _regime_vote_of(sig_nomatch, regime=RegimeLabel.RANGE_MARKET)
    assert v_nomatch.vote == "reduce_size"
    assert v_nomatch.score == 5.0


def test_confidence_0_and_10_produce_identical_regime_vote():
    common = dict(
        strategy_name="KDA_AUTHORITY",
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED",
    )
    v_low  = _regime_vote_of(_sig(confidence=0.0,  **common))
    v_high = _regime_vote_of(_sig(confidence=10.0, **common))

    assert v_low.vote == v_high.vote
    assert v_low.score == v_high.score
    assert v_low.suggested_position_modifier == v_high.suggested_position_modifier
    assert v_low.reasoning == v_high.reasoning


def test_strategy_name_independence_for_qualifying_population():
    common = dict(
        confidence=6.0,
        kda_decision="KNOWLEDGE_BUY", authorization_source="BOTH",
        kda_evidence_state="VALIDATED",
    )
    v_named = _regime_vote_of(_sig(strategy_name="Mean_Reversion_RSI_HiVol", **common))
    v_kda   = _regime_vote_of(_sig(strategy_name="KDA_AUTHORITY", **common))
    assert v_named.vote == v_kda.vote
    assert v_named.score == v_kda.score
    assert v_named.suggested_position_modifier == v_kda.suggested_position_modifier


def test_partial_match_authorization_source_strategy_lab_not_exempted():
    # kda_decision + evidence_state qualify, but authorization_source does not
    # -> the three conditions are conjunctive, not disjunctive.
    sig = _sig(strategy_name="Equity_Breakout", confidence=6.0,
               kda_decision="KNOWLEDGE_BUY", authorization_source="STRATEGY_LAB",
               kda_evidence_state="VALIDATED")
    v = _regime_vote_of(sig, regime=RegimeLabel.RANGE_MARKET)
    assert v.vote == "reduce_size"
    assert v.score == 5.0
