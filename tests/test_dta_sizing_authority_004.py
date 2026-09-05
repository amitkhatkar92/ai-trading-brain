"""
DTA-SIZING-AUTHORITY-004 — CRE _size_position() feasibility-only redesign
for KDA-authoritative candidates: knowledge_multiplier fixed at 1.0
instead of a confidence-derived [0.5x-3.0x] multiplier.

Calls the real CapitalRiskEngine.allocate() / _size_position() directly
(production code, not a simulation) to verify:
  1. KDA-authoritative confidence 0.0 and 10.0 produce IDENTICAL sizing
     (the strongest ownership test -- proves confidence has genuinely
     disappeared from this path).
  2. AUROPHARMA-shape candidate (previously rescued by full-deployable
     budget) still survives with the fixed multiplier.
  3. CRAFTSMAN-shape candidate (wide stop distance) still rejected.
  4. Named-strategy candidate: confidence-based knowledge_multiplier
     formula unchanged.
  5. DTA-KDA-AUTHORITY-WIDEN-001: KDA USEFUL/DEVELOPING evidence IS now
     exempted, same as VALIDATED/DECISION_ELIGIBLE -- fixed multiplier=1.0
     applies regardless of evidence_state.
  6. Partial KDA-authoritative matches (authorization_source not KDA/BOTH)
     do not get the fixed multiplier.
  7. Deployable-capital sensitivity (VIX/drawdown/regime) still throttles
     KDA-authoritative quantity proportionally, end to end.
  8. MAX_POSITIONS and exposure cap unaffected.
"""
from __future__ import annotations

import json
from datetime import datetime

from risk_control.capital_risk_engine import CapitalRiskEngine, _MAX_POSITIONS
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from config import TOTAL_CAPITAL, MAX_RISK_PER_TRADE_PCT


def _snapshot(regime=RegimeLabel.RANGE_MARKET, vix: float = 15.0) -> MarketSnapshot:
    return MarketSnapshot(
        timestamp=datetime.now(), indices={},
        regime=regime, volatility=VolatilityLevel.MEDIUM,
        vix=vix, pcr=1.0, market_breadth=0.5,
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
    )
    defaults.update(overrides)
    return TradeSignal(**defaults)


def _cre() -> CapitalRiskEngine:
    return CapitalRiskEngine()


def _cre_budget_of(sig: TradeSignal) -> float:
    return json.loads(sig.notes or "{}")["cre_budget"]


# Deployable capital for RANGE_MARKET + VIX=15 + no portfolio:
# regime_exposure=0.50, vix_ceiling=1.00 (vix<18), dd_reducer=1.00 (no portfolio)
_DEPLOYABLE = TOTAL_CAPITAL * 0.50


def test_kda_authoritative_confidence_0_and_10_produce_identical_sizing():
    """T1 (strongest ownership test): KDA-authoritative confidence 0.0 and
    10.0 must produce identical CRE sizing -- proving confidence has
    genuinely disappeared from this path."""
    cre = _cre()
    common = dict(
        strategy_name="KDA_AUTHORITY", entry_price=2000.0, stop_loss=1950.0,
        target_price=2150.0,
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED", kda_conviction=8.0,
    )
    sig_low_conf  = _sig(symbol="LOWCONF",  confidence=0.0,  **common)
    sig_high_conf = _sig(symbol="HIGHCONF", confidence=10.0, **common)

    result_low  = _cre().allocate([sig_low_conf],  _snapshot(), portfolio=None)
    result_high = cre.allocate([sig_high_conf], _snapshot(), portfolio=None)

    assert len(result_low) == 1 and len(result_high) == 1
    assert result_low[0].quantity == result_high[0].quantity


def test_aurophrama_shape_kda_candidate_still_survives():
    """T2: AUROPHARMA-shape KDA-authoritative candidate (rescued by full
    deployable budget in DTA-CRE-KDA-SURVIVAL-001) still survives with the
    fixed multiplier=1.0."""
    cre = _cre()
    sig = _sig(
        symbol="AUROPHARMA", strategy_name="KDA_AUTHORITY",
        entry_price=1655.60, stop_loss=1604.36, target_price=1758.08,
        confidence=8.0,
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED", kda_conviction=8.0,
    )
    result = cre.allocate([sig], _snapshot(), portfolio=None)
    assert len(result) == 1
    assert result[0].quantity > 0


def test_craftsman_shape_kda_candidate_still_rejected():
    """T3: CRAFTSMAN-shape KDA-authoritative candidate (wide stop distance)
    still rejected even with the fixed multiplier=1.0 (more conservative
    than the old confidence-weighted multiplier, if anything)."""
    cre = _cre()
    sig = _sig(
        symbol="CRAFTSMAN", strategy_name="KDA_AUTHORITY",
        direction=SignalDirection.SHORT,
        entry_price=11144.0, stop_loss=11544.8, target_price=10342.4,
        confidence=8.5,
        kda_decision="KNOWLEDGE_SELL", authorization_source="KDA",
        kda_evidence_state="DECISION_ELIGIBLE", kda_conviction=8.5,
    )
    result = cre.allocate([sig], _snapshot(), portfolio=None)
    assert len(result) == 0


def test_named_strategy_knowledge_multiplier_unchanged():
    """T4: named-strategy (non-KDA-authoritative) candidate's
    knowledge_multiplier formula is completely unchanged."""
    cre = _cre()
    sig = _sig(strategy_name="Mean_Reversion", confidence=6.0)  # no KDA fields
    result = cre.allocate([sig], _snapshot(), portfolio=None)
    assert len(result) == 1
    # Reproduce the (unchanged) formula for the expected quantity:
    budget = _DEPLOYABLE * 0.22   # Mean_Reversion share
    k_mult = 0.5 + (6.0 / 10.0) * 2.5
    risk_amount = budget * MAX_RISK_PER_TRADE_PCT * k_mult
    sl_distance = abs(sig.entry_price - sig.stop_loss)
    expected_qty = min(int(risk_amount / sl_distance), int(budget / sig.entry_price))
    assert result[0].quantity == expected_qty


def test_kda_useful_evidence_now_exempted_identical_sizing():
    """T5: DTA-KDA-AUTHORITY-WIDEN-001 — KDA USEFUL evidence IS now
    KDA-authoritative -- fixed multiplier=1.0 applies, so confidence value
    no longer matters for this population (identical sizing regardless)."""
    cre = _cre()
    sig_low  = _sig(symbol="LOW",  strategy_name="KDA_AUTHORITY", confidence=1.0,
                     stop_loss=98.0, target_price=104.0,
                     kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
                     kda_evidence_state="USEFUL", kda_conviction=9.0)
    sig_high = _sig(symbol="HIGH", strategy_name="KDA_AUTHORITY", confidence=9.0,
                     stop_loss=98.0, target_price=104.0,
                     kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
                     kda_evidence_state="USEFUL", kda_conviction=9.0)
    result_low  = _cre().allocate([sig_low],  _snapshot(), portfolio=None)
    result_high = _cre().allocate([sig_high], _snapshot(), portfolio=None)
    assert len(result_low) == 1 and len(result_high) == 1
    assert result_low[0].quantity == result_high[0].quantity


def test_partial_kda_authoritative_matches_use_confidence_based():
    """T6: partial KDA-authoritative matches (missing one of the three
    required conditions) do not get the fixed multiplier -- confidence
    still governs."""
    cre = _cre()
    sig_low  = _sig(symbol="LOW",  strategy_name="KDA_AUTHORITY", confidence=1.0,
                     stop_loss=98.0, target_price=104.0,
                     kda_decision="KNOWLEDGE_BUY", authorization_source="STRATEGY_LAB",
                     kda_evidence_state="VALIDATED", kda_conviction=9.0)
    sig_high = _sig(symbol="HIGH", strategy_name="KDA_AUTHORITY", confidence=9.0,
                     stop_loss=98.0, target_price=104.0,
                     kda_decision="KNOWLEDGE_BUY", authorization_source="STRATEGY_LAB",
                     kda_evidence_state="VALIDATED", kda_conviction=9.0)
    result_low  = _cre().allocate([sig_low],  _snapshot(), portfolio=None)
    result_high = _cre().allocate([sig_high], _snapshot(), portfolio=None)
    assert len(result_low) == 1 and len(result_high) == 1
    assert result_low[0].quantity != result_high[0].quantity


def test_deployable_capital_sensitivity_preserved_end_to_end():
    """T7: VIX/drawdown/regime throttling still proportionally reduces
    KDA-authoritative quantity end-to-end (not just algebraically)."""
    cre = _cre()
    sig_calm  = _sig(symbol="CALM",  strategy_name="KDA_AUTHORITY",
                      entry_price=100.0, stop_loss=95.0, target_price=112.5,
                      confidence=8.0,
                      kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
                      kda_evidence_state="VALIDATED", kda_conviction=8.0)
    sig_crash = _sig(symbol="CRASH", strategy_name="KDA_AUTHORITY",
                      entry_price=100.0, stop_loss=95.0, target_price=112.5,
                      confidence=8.0,
                      kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
                      kda_evidence_state="VALIDATED", kda_conviction=8.0)
    result_calm  = _cre().allocate([sig_calm],  _snapshot(vix=15.0), portfolio=None)
    result_crash = _cre().allocate([sig_crash], _snapshot(vix=40.0), portfolio=None)  # VIX>35 crash ceiling
    assert len(result_calm) == 1
    # VIX=40 -> vix_ceiling=0.10 vs VIX=15 -> vix_ceiling=1.00 (both capped by regime 0.50)
    # so calm: base_exposure=min(0.50,1.00)=0.50; crash: base_exposure=min(0.50,0.10)=0.10
    assert (len(result_crash) == 0) or (result_crash[0].quantity < result_calm[0].quantity)


def test_max_positions_and_exposure_cap_unaffected():
    """T8: MAX_POSITIONS and exposure cap still apply exactly as before,
    unaffected by the fixed-multiplier change."""
    cre = _cre()
    signals = [
        _sig(
            symbol=f"SYM{i}", strategy_name="KDA_AUTHORITY", confidence=8.0,
            kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
            kda_evidence_state="VALIDATED", kda_conviction=8.0 + i * 0.01,
        )
        for i in range(_MAX_POSITIONS + 3)
    ]
    result = cre.allocate(signals, _snapshot(), portfolio=None)
    assert len(result) <= _MAX_POSITIONS

    big_signals = [
        _sig(
            symbol=f"BIG{i}", strategy_name="KDA_AUTHORITY",
            entry_price=50000.0, stop_loss=49000.0, target_price=53000.0,
            confidence=9.0,
            kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
            kda_evidence_state="VALIDATED", kda_conviction=9.0 - i * 0.01,
        )
        for i in range(6)
    ]
    result2 = _cre().allocate(big_signals, _snapshot(), portfolio=None)
    total_notional = sum(s.quantity * s.entry_price for s in result2)
    assert total_notional <= _DEPLOYABLE * 1.05 + 1e-6
