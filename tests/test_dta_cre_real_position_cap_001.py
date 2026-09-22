"""
tests/test_dta_cre_real_position_cap_001.py
=============================================
DTA-CRE-REAL-POSITION-CAP-001 (superseded/extended by DTA-CRE-LATE-CAP-001)

Original finding: CapitalRiskEngine.allocate() computed _cre_available
(_MAX_POSITIONS - real open positions) purely for an audit log line, but
the actual cap loop gated on `len(result) >= _MAX_POSITIONS` -- completely
ignoring how many positions were already open.

DTA-CRE-LATE-CAP-001 follow-up (architectural fix, same day): the real
"how many new positions can we open" decision was moved OUT of
CapitalRiskEngine entirely -- it's now enforced once, at the very end of
the pipeline (right before execution, in orchestrator/master_orchestrator.py's
STEP 6), ranked by Debate/KDA's own final confidence_score. CRE's own
cutoff is now a widened, open-position-agnostic "evaluation pool"
(_CRE_EVAL_POOL_MULTIPLIER x _MAX_POSITIONS, bounded by
_CRE_EVAL_POOL_MAX_ABS) -- a compute-cost guard for the expensive
downstream stages (Simulation/RiskGuardian/Debate), not a capital/exposure
constraint. This lets a signal that would previously have been discarded
before Debate ever saw it get a real chance to be evaluated.

This file now verifies CRE's own (new) responsibility: the eval-pool
widening, and that it is NOT open-position-aware (that concern moved
downstream -- see tests/test_dta_cre_late_cap_001.py for the real cap).
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from risk_control.capital_risk_engine import (
    CapitalRiskEngine, _MAX_POSITIONS,
    _CRE_EVAL_POOL_MULTIPLIER, _CRE_EVAL_POOL_MAX_ABS,
)
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from models.portfolio import Portfolio, Position

_EVAL_POOL = min(_CRE_EVAL_POOL_MAX_ABS,
                  max(_MAX_POSITIONS, _MAX_POSITIONS * _CRE_EVAL_POOL_MULTIPLIER))


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


def test_t01_pool_wider_than_max_positions():
    """Sanity: the widened eval pool must be strictly larger than the real
    MAX_POSITIONS (otherwise the whole point of DTA-CRE-LATE-CAP-001 --
    letting more candidates reach Debate -- would not hold)."""
    assert _EVAL_POOL > _MAX_POSITIONS


def test_t02_eval_pool_is_open_position_agnostic():
    """CRE's cutoff no longer depends on real open positions at all -- that
    concern moved downstream to the final execution-time cap. Same
    candidate count, 0 vs many open positions, must produce the same
    CRE-stage result count."""
    cre = CapitalRiskEngine()
    signals = [_sig(symbol=f"SYM{i}") for i in range(_EVAL_POOL + 3)]

    result_zero_open = cre.allocate(
        signals, _snapshot(), portfolio=_portfolio_with_open_positions(0)
    )
    result_many_open = CapitalRiskEngine().allocate(
        signals, _snapshot(), portfolio=_portfolio_with_open_positions(_MAX_POSITIONS)
    )
    assert len(result_zero_open) == len(result_many_open) == _EVAL_POOL


def test_t03_eval_pool_cutoff_applies():
    """More candidates than the eval pool -> capped at exactly the pool size."""
    cre = CapitalRiskEngine()
    signals = [_sig(symbol=f"SYM{i}") for i in range(_EVAL_POOL + 5)]
    result = cre.allocate(signals, _snapshot(), portfolio=None)
    assert len(result) == _EVAL_POOL


def test_t04_fewer_candidates_than_pool_all_pass():
    """Fewer candidates than the eval pool -> none rejected for capacity."""
    cre = CapitalRiskEngine()
    signals = [_sig(symbol=f"SYM{i}") for i in range(min(3, _MAX_POSITIONS))]
    result = cre.allocate(signals, _snapshot(), portfolio=None)
    assert len(result) == len(signals)


def test_t05_portfolio_none_still_uses_eval_pool():
    """portfolio=None (no portfolio info available) must still apply the
    eval-pool cutoff -- unaffected either way, since the cutoff no longer
    reads portfolio state at all."""
    cre = CapitalRiskEngine()
    signals = [_sig(symbol=f"SYM{i}") for i in range(_EVAL_POOL + 3)]
    result = cre.allocate(signals, _snapshot(), portfolio=None)
    assert len(result) == _EVAL_POOL


def test_t06_audit_block_exception_fails_safe_to_eval_pool():
    """If the position-count audit computation itself raises, allocate()
    must still fail safe to the eval-pool cutoff, not crash and not
    silently allow unlimited signals."""
    cre = CapitalRiskEngine()
    signals = [_sig(symbol=f"SYM{i}") for i in range(_EVAL_POOL + 3)]

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
    assert len(result) == _EVAL_POOL


def test_t07_overflow_signals_still_tagged_max_positions_cap(monkeypatch):
    """Rejected overflow signals are still persisted with
    reason=MAX_POSITIONS_CAP (label unchanged, only the threshold moved)."""
    mock_tracker = MagicMock()
    monkeypatch.setattr(
        "analysis.rejection_tracker.get_rejection_tracker", lambda: mock_tracker
    )
    cre = CapitalRiskEngine()
    signals = [_sig(symbol=f"SYM{i}") for i in range(_EVAL_POOL + 2)]
    result = cre.allocate(signals, _snapshot(), portfolio=None)
    assert len(result) == _EVAL_POOL
    assert mock_tracker.ingest_rejection.called
    reasons = {
        c.kwargs.get("rejected_reason") for c in mock_tracker.ingest_rejection.call_args_list
    }
    assert "MAX_POSITIONS_CAP" in reasons

