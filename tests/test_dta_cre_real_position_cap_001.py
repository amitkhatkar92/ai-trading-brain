"""
tests/test_dta_cre_real_position_cap_001.py
=============================================
DTA-CRE-REAL-POSITION-CAP-001

Root cause: CapitalRiskEngine.allocate() computed _cre_available
(_MAX_POSITIONS - real open positions) purely for an audit log line, but
the actual cap loop gated on `len(result) >= _MAX_POSITIONS` -- completely
ignoring how many positions were already open. With 0 open positions
(the common case for this account) this happened to look correct, which
masked the bug: whenever real positions WERE open, the cap silently
allowed up to _MAX_POSITIONS *additional* new signals on top of the
already-open ones, breaching the intended total-exposure limit.

Fix: the loop now gates on `len(result) >= _cre_available`, where
_cre_available = max(0, _MAX_POSITIONS - open_positions). With 0 open
positions this is identical to the old behavior (regression-proof).
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from risk_control.capital_risk_engine import CapitalRiskEngine, _MAX_POSITIONS
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from models.portfolio import Portfolio, Position


def _snapshot(regime=RegimeLabel.RANGE_MARKET, vix: float = 15.0) -> MarketSnapshot:
    return MarketSnapshot(
        timestamp=datetime.now(), indices={},
        regime=regime, volatility=VolatilityLevel.MEDIUM,
        vix=vix, pcr=1.0, market_breadth=0.5,
    )


def _sig(**overrides) -> TradeSignal:
    defaults = dict(
        symbol="TESTSTOCK", direction=SignalDirection.BUY,
        signal_type=SignalType.EQUITY, entry_price=100.0, stop_loss=95.0,
        target_price=112.5, confidence=8.0, strategy_name="KDA_AUTHORITY",
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED", kda_conviction=8.0,
    )
    defaults.update(overrides)
    return TradeSignal(**defaults)


def _portfolio_with_open_positions(n: int) -> Portfolio:
    pf = Portfolio(capital=50_000.0)
    for i in range(n):
        pf.positions[f"OPEN{i}"] = Position(
            symbol=f"OPEN{i}", quantity=1, avg_entry_price=100.0,
        )
    return pf


def test_t01_zero_open_positions_unchanged_behavior():
    """Regression guard: with 0 real open positions, the cap is still
    exactly _MAX_POSITIONS per cycle -- identical to pre-fix behavior."""
    cre = CapitalRiskEngine()
    signals = [_sig(symbol=f"SYM{i}") for i in range(_MAX_POSITIONS + 3)]
    result = cre.allocate(signals, _snapshot(), portfolio=_portfolio_with_open_positions(0))
    assert len(result) == _MAX_POSITIONS


def test_t02_open_positions_reduce_available_slots():
    """With 2 real open positions and _MAX_POSITIONS=5, only 3 new signals
    should be allowed through -- not 5."""
    cre = CapitalRiskEngine()
    n_open = 2
    signals = [_sig(symbol=f"SYM{i}") for i in range(_MAX_POSITIONS + 3)]
    result = cre.allocate(
        signals, _snapshot(), portfolio=_portfolio_with_open_positions(n_open)
    )
    assert len(result) == max(0, _MAX_POSITIONS - n_open)


def test_t03_already_at_or_over_cap_allows_zero_new_signals():
    """With open positions already >= _MAX_POSITIONS, zero new signals
    should be approved this cycle -- all rejected as MAX_POSITIONS_CAP."""
    cre = CapitalRiskEngine()
    signals = [_sig(symbol=f"SYM{i}") for i in range(5)]
    result = cre.allocate(
        signals, _snapshot(), portfolio=_portfolio_with_open_positions(_MAX_POSITIONS)
    )
    assert result == []


def test_t04_portfolio_none_still_uses_full_cap():
    """portfolio=None (no portfolio info available) must fail-safe to the
    full _MAX_POSITIONS cap, not zero."""
    cre = CapitalRiskEngine()
    signals = [_sig(symbol=f"SYM{i}") for i in range(_MAX_POSITIONS + 3)]
    result = cre.allocate(signals, _snapshot(), portfolio=None)
    assert len(result) == _MAX_POSITIONS


def test_t05_audit_block_exception_fails_safe_to_full_cap():
    """If the position-count audit computation itself raises, allocate()
    must still fail safe to the original _MAX_POSITIONS cap, not crash
    and not silently allow unlimited signals."""
    cre = CapitalRiskEngine()
    signals = [_sig(symbol=f"SYM{i}") for i in range(_MAX_POSITIONS + 3)]

    class _BrokenPositions:
        def values(self):
            raise RuntimeError("boom")

    class _FakePortfolio:
        """Duck-typed fake — drawdown_pct is a plain attribute here (unlike
        the real Portfolio's property) so it never touches .positions,
        isolating the failure to exactly the audit block under test."""
        drawdown_pct = 0.0

        def __init__(self):
            self.positions = _BrokenPositions()

    result = cre.allocate(signals, _snapshot(), portfolio=_FakePortfolio())
    assert len(result) == _MAX_POSITIONS


def test_t06_overflow_signals_still_tagged_max_positions_cap(monkeypatch):
    """Rejected overflow signals (due to real open positions) are still
    persisted with reason=MAX_POSITIONS_CAP, same as before."""
    mock_tracker = MagicMock()
    monkeypatch.setattr(
        "analysis.rejection_tracker.get_rejection_tracker", lambda: mock_tracker
    )
    cre = CapitalRiskEngine()
    signals = [_sig(symbol=f"SYM{i}") for i in range(_MAX_POSITIONS)]
    result = cre.allocate(
        signals, _snapshot(), portfolio=_portfolio_with_open_positions(_MAX_POSITIONS - 1)
    )
    assert len(result) == 1
    assert mock_tracker.ingest_rejection.called
    reasons = {
        c.kwargs.get("rejected_reason") for c in mock_tracker.ingest_rejection.call_args_list
    }
    assert "MAX_POSITIONS_CAP" in reasons
