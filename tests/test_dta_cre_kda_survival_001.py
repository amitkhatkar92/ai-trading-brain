"""
DTA-CRE-KDA-SURVIVAL-001 — CapitalRiskEngine.allocate() feasibility check
for KDA-authoritative candidates uses the full deployable pool instead of
the per-strategy budget share.

Calls the real CapitalRiskEngine.allocate() directly (production code,
not a simulation) to verify:
  1. KDA-authoritative candidate is feasibility-checked against the full
     deployable pool (confirmed via the persisted cre_budget metadata).
  2. A KDA candidate that would be CRE_QTY_ZERO'd under the old 10%
     strategy-share budget now survives when the strategy budget was the
     only blocker.
  3. A KDA candidate with a genuinely wide stop distance still gets
     rejected even against the full deployable pool (real risk limit).
  4. A named-strategy (non-KDA-authoritative) candidate still uses
     _strategy_budget() unchanged.
  5. MAX_POSITIONS cap is unaffected.
  6. Exposure cap is unaffected.
  7. Ranking remains kda_conviction-based (unaffected by this change).
"""
from __future__ import annotations

import json
from datetime import datetime

from risk_control.capital_risk_engine import CapitalRiskEngine
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from config import TOTAL_CAPITAL


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
    """Read the persisted cre_budget metadata CRE writes for surviving signals."""
    meta = json.loads(sig.notes or "{}")
    return meta["cre_budget"]


# Deployable capital for RANGE_MARKET + VIX=15 + no portfolio:
# regime_exposure=0.50, vix_ceiling=1.00 (vix<18), dd_reducer=1.00 (no portfolio)
_DEPLOYABLE = TOTAL_CAPITAL * 0.50


def test_kda_authoritative_uses_full_deployable_as_budget():
    """T1: KDA-authoritative candidate's cre_budget equals the full deployable
    pool, not a strategy-share fraction of it."""
    cre = _cre()
    sig = _sig(
        strategy_name="KDA_AUTHORITY",
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED", kda_conviction=8.0,
    )
    result = cre.allocate([sig], _snapshot(), portfolio=None)
    assert len(result) == 1
    assert _cre_budget_of(result[0]) == int(_DEPLOYABLE)


def test_kda_candidate_previously_budget_blocked_now_survives():
    """T2: a KDA-authoritative candidate whose only blocker was the 10%
    strategy-share budget now survives with the full deployable pool.

    Entry/stop chosen so that budget = deployable*0.10 (old default share)
    would produce qty_by_risk = 0, but budget = full deployable produces
    qty > 0 -- mirrors the real AUROPHARMA case from the production audit.
    """
    from config import MAX_RISK_PER_TRADE_PCT
    old_default_budget = _DEPLOYABLE * 0.10
    entry, stop = 2000.0, 1950.0   # stop distance = 50
    k_mult = 0.5 + (8.0 / 10.0) * 2.5   # confidence/kda_conviction = 8.0 -> 2.5
    old_risk_amount = old_default_budget * MAX_RISK_PER_TRADE_PCT * k_mult
    assert int(old_risk_amount / 50.0) == 0, "test setup must reproduce the old QTY_ZERO case"
    new_risk_amount = _DEPLOYABLE * MAX_RISK_PER_TRADE_PCT * k_mult
    assert int(new_risk_amount / 50.0) > 0, "test setup must produce a survivable qty with full deployable"

    cre = _cre()
    sig = _sig(
        strategy_name="KDA_AUTHORITY", entry_price=entry, stop_loss=stop,
        target_price=entry + 3 * 50, confidence=8.0,
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED", kda_conviction=8.0,
    )
    result = cre.allocate([sig], _snapshot(), portfolio=None)
    assert len(result) == 1, "candidate should now survive CRE with the full deployable budget"
    assert result[0].quantity > 0


def test_kda_candidate_with_wide_stop_still_rejected():
    """T3: a KDA-authoritative candidate with a genuinely wide stop distance
    (mirrors CRAFTSMAN) is still rejected even against the full deployable
    pool -- MAX_RISK_PER_TRADE_PCT is a real, unrelated risk limit."""
    from config import MAX_RISK_PER_TRADE_PCT
    entry, stop = 11144.0, 11544.8   # stop distance = 400.8 (wide, ~3.6% of price)
    k_mult = 0.5 + (8.5 / 10.0) * 2.5
    risk_amount = _DEPLOYABLE * MAX_RISK_PER_TRADE_PCT * k_mult
    assert int(risk_amount / 400.8) == 0, "test setup must reproduce a genuine risk-limit rejection"

    cre = _cre()
    sig = _sig(
        strategy_name="KDA_AUTHORITY", direction=SignalDirection.SHORT,
        entry_price=entry, stop_loss=stop, target_price=entry - 3 * 400.8,
        confidence=8.5,
        kda_decision="KNOWLEDGE_SELL", authorization_source="KDA",
        kda_evidence_state="DECISION_ELIGIBLE", kda_conviction=8.5,
    )
    result = cre.allocate([sig], _snapshot(), portfolio=None)
    assert len(result) == 0, "genuinely wide-stop candidate should still be rejected"


def test_named_strategy_still_uses_strategy_budget():
    """T4: a non-KDA-authoritative (named-strategy) candidate's cre_budget
    is still the strategy-share fraction of deployable, unchanged."""
    cre = _cre()
    sig = _sig(strategy_name="Mean_Reversion", confidence=7.0)  # no KDA fields at all
    result = cre.allocate([sig], _snapshot(), portfolio=None)
    assert len(result) == 1
    assert _cre_budget_of(result[0]) == int(_DEPLOYABLE * 0.22)  # Mean_Reversion share


def test_kda_useful_evidence_now_exempted_uses_full_deployable():
    """T4b: DTA-KDA-AUTHORITY-WIDEN-001 — KDA USEFUL evidence IS now
    KDA-authoritative, same as VALIDATED/DECISION_ELIGIBLE -- uses the full
    deployable pool, not the strategy-share budget."""
    cre = _cre()
    sig = _sig(
        strategy_name="KDA_AUTHORITY", confidence=7.0,
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="USEFUL", kda_conviction=6.0,
    )
    result = cre.allocate([sig], _snapshot(), portfolio=None)
    assert len(result) == 1
    assert _cre_budget_of(result[0]) == int(_DEPLOYABLE)


def test_max_positions_cap_unaffected():
    """T5: MAX_POSITIONS still caps total surviving signals, regardless of
    how any individual candidate's budget was computed."""
    from risk_control.capital_risk_engine import _MAX_POSITIONS
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


def test_exposure_cap_unaffected():
    """T6: cumulative exposure cap still rejects once allocated_total would
    exceed deployable*1.05, unchanged by the budget-source change."""
    cre = _cre()
    # Large entry price + large quantity potential -> big notional per trade,
    # several of these should trip the exposure cap well before MAX_POSITIONS.
    signals = [
        _sig(
            symbol=f"BIG{i}", strategy_name="KDA_AUTHORITY",
            entry_price=50000.0, stop_loss=49000.0, target_price=53000.0,
            confidence=9.0,
            kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
            kda_evidence_state="VALIDATED", kda_conviction=9.0 - i * 0.01,
        )
        for i in range(6)
    ]
    result = cre.allocate(signals, _snapshot(), portfolio=None)
    total_notional = sum(s.quantity * s.entry_price for s in result)
    assert total_notional <= _DEPLOYABLE * 1.05 + 1e-6


def test_ranking_remains_kda_conviction_based():
    """T7: quality-sort ranking is unaffected -- higher kda_conviction still
    ranks first (same as before this change)."""
    cre = _cre()
    weak = _sig(
        symbol="WEAK", strategy_name="KDA_AUTHORITY", confidence=7.0,
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED", kda_conviction=7.0,
    )
    strong = _sig(
        symbol="STRONG", strategy_name="KDA_AUTHORITY", confidence=7.0,
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED", kda_conviction=9.5,
    )
    result = cre.allocate([weak, strong], _snapshot(), portfolio=None)
    assert [s.symbol for s in result] == ["STRONG", "WEAK"]
