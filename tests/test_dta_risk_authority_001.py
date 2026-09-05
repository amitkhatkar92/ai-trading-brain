"""
DTA-RISK-AUTHORITY-001 — RiskManagerAI confidence-floor exemption for
KDA-authoritative candidates.

Calls the real RiskManagerAI._check() method directly (production code,
not a simulation) to verify:
  1. KDA-authoritative + confidence 6.0 → confidence gate does NOT reject;
     remaining risk gates still execute.
  2. KDA-authoritative + confidence 8.0 → unchanged.
  3. Non-KDA + confidence 6.0 → existing 6.8 rejection remains.
  4. KDA USEFUL/DEVELOPING + confidence 6.0 → existing confidence gate remains.
  5. KDA-authoritative definition requires the complete established
     authorization/evidence combination (partial matches do not exempt).
  6. Existing R:R / stop / per-trade-risk / portfolio-heat / duplicate-symbol
     behavior remains unchanged.
"""
from __future__ import annotations

from risk_control.risk_manager_ai import RiskManagerAI
from models.trade_signal import TradeSignal, SignalDirection, SignalType


def _sig(**overrides) -> TradeSignal:
    defaults = dict(
        symbol="TESTSTOCK",
        direction=SignalDirection.BUY,
        signal_type=SignalType.EQUITY,
        entry_price=100.0,
        stop_loss=95.0,
        target_price=112.5,   # RR = 2.5
        confidence=6.0,
        atr=5.0,   # ATR-sized signal — exempts gate #4 (stop-distance sanity),
                   # matching how real scanner/KDA signals are constructed
    )
    defaults.update(overrides)
    return TradeSignal(**defaults)


def _rm() -> RiskManagerAI:
    rm = RiskManagerAI()
    rm._current_portfolio_heat = 0.0
    return rm


def test_kda_authoritative_low_confidence_not_rejected_on_confidence():
    """T1: KDA-authoritative + confidence 6.0 → passes (no confidence rejection)."""
    rm = _rm()
    sig = _sig(
        confidence=6.0,
        kda_decision="KNOWLEDGE_BUY",
        authorization_source="KDA",
        kda_evidence_state="VALIDATED",
    )
    reason = rm._check(sig, seen=set())
    assert reason is None, f"expected pass, got rejection: {reason}"


def test_kda_authoritative_high_confidence_unchanged():
    """T2: KDA-authoritative + confidence 8.0 → unchanged (still passes)."""
    rm = _rm()
    sig = _sig(
        confidence=8.0,
        kda_decision="KNOWLEDGE_SELL",
        authorization_source="BOTH",
        kda_evidence_state="DECISION_ELIGIBLE",
    )
    reason = rm._check(sig, seen=set())
    assert reason is None


def test_non_kda_low_confidence_still_rejected():
    """T3: Non-KDA + confidence 6.0 → existing 6.8 rejection remains."""
    rm = _rm()
    sig = _sig(confidence=6.0)  # no KDA fields at all
    reason = rm._check(sig, seen=set())
    assert reason is not None
    assert "Confidence" in reason and "6.0" in reason


def test_kda_useful_evidence_low_confidence_exempted():
    """T4: DTA-KDA-AUTHORITY-WIDEN-001 — KDA USEFUL evidence + confidence 6.0
    is now exempt from the confidence floor; evidence_state only shapes KDA's
    own decision, not what happens after it authorizes BUY/SELL."""
    rm = _rm()
    sig = _sig(
        confidence=6.0,
        kda_decision="KNOWLEDGE_BUY",
        authorization_source="KDA",
        kda_evidence_state="USEFUL",
    )
    reason = rm._check(sig, seen=set())
    assert reason is None, f"expected pass, got rejection: {reason}"


def test_kda_developing_evidence_low_confidence_exempted():
    """T4b: DTA-KDA-AUTHORITY-WIDEN-001 — KDA DEVELOPING evidence + confidence
    6.0 is now exempt from the confidence floor, same as VALIDATED/USEFUL."""
    rm = _rm()
    sig = _sig(
        confidence=6.0,
        kda_decision="KNOWLEDGE_BUY",
        authorization_source="KDA",
        kda_evidence_state="DEVELOPING",
    )
    reason = rm._check(sig, seen=set())
    assert reason is None, f"expected pass, got rejection: {reason}"


def test_kda_authoritative_requires_full_combination_partial_matches_do_not_exempt():
    """T5: partial KDA-authoritative matches (missing one of the two required
    conditions: kda_decision BUY/SELL, authorization_source KDA/BOTH) do NOT
    exempt the confidence floor. DTA-KDA-AUTHORITY-WIDEN-001: evidence_state
    is no longer one of the required conditions — a missing/None evidence_state
    alone no longer disqualifies the exemption (covered by a separate test)."""
    rm = _rm()

    # Missing authorization_source
    sig_a = _sig(confidence=6.0, kda_decision="KNOWLEDGE_BUY",
                 authorization_source=None, kda_evidence_state="VALIDATED")
    assert rm._check(sig_a, seen=set()) is not None

    # kda_decision is KNOWLEDGE_WAIT, not BUY/SELL
    sig_c = _sig(confidence=6.0, kda_decision="KNOWLEDGE_WAIT",
                 authorization_source="KDA", kda_evidence_state="VALIDATED")
    assert rm._check(sig_c, seen=set()) is not None

    # authorization_source is STRATEGY_LAB, not KDA/BOTH
    sig_d = _sig(confidence=6.0, kda_decision="KNOWLEDGE_BUY",
                 authorization_source="STRATEGY_LAB", kda_evidence_state="VALIDATED")
    assert rm._check(sig_d, seen=set()) is not None


def test_kda_authoritative_missing_evidence_state_still_exempt():
    """T5b: DTA-KDA-AUTHORITY-WIDEN-001 — a KDA-authorized signal with no
    evidence_state recorded (None) is still exempt from the confidence floor;
    evidence_state is no longer part of the exemption condition at all."""
    rm = _rm()
    sig = _sig(confidence=6.0, kda_decision="KNOWLEDGE_BUY",
               authorization_source="KDA", kda_evidence_state=None)
    assert rm._check(sig, seen=set()) is None


def test_rr_gate_unchanged_for_kda_authoritative():
    """T6a: R:R gate still rejects a KDA-authoritative signal with weak R:R."""
    rm = _rm()
    sig = _sig(
        confidence=6.0, entry_price=100.0, stop_loss=95.0, target_price=105.0,  # RR = 1.0
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED",
    )
    reason = rm._check(sig, seen=set())
    assert reason is not None and "R:R" in reason


def test_stop_loss_gate_unchanged_for_kda_authoritative():
    """T6b: stop-loss-defined gate still rejects a KDA-authoritative signal
    with no stop loss."""
    rm = _rm()
    sig = _sig(
        confidence=6.0, stop_loss=0.0,
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED",
    )
    reason = rm._check(sig, seen=set())
    assert reason == "No stop loss defined"


def test_portfolio_heat_gate_unchanged_for_kda_authoritative():
    """T6c: portfolio heat gate still rejects a KDA-authoritative signal
    when heat is already at the cap."""
    from config import MAX_PORTFOLIO_RISK_PCT
    rm = _rm()
    rm._current_portfolio_heat = MAX_PORTFOLIO_RISK_PCT  # already at/over cap
    sig = _sig(
        confidence=6.0,
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED",
    )
    reason = rm._check(sig, seen=set())
    assert reason is not None and "Portfolio heat" in reason


def test_duplicate_symbol_gate_unchanged_for_kda_authoritative():
    """T6d: duplicate-symbol gate still rejects a KDA-authoritative signal
    whose symbol was already seen this cycle."""
    rm = _rm()
    sig = _sig(
        confidence=6.0,
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED",
    )
    reason = rm._check(sig, seen={"TESTSTOCK"})
    assert reason == "Duplicate symbol TESTSTOCK"
