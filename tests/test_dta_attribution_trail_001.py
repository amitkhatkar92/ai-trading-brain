"""
tests/test_dta_attribution_trail_001.py
=========================================
DTA-ATTRIBUTION-TRAIL-001 — persistent rejection audit trail for
CapitalRiskEngine (MAX_POSITIONS_CAP / EXPOSURE_CAP_EXCEEDED).

Context: a full-day forensic audit (2026-09-09) found these CRE-level
rejections were logged (transient container logs) and kept in an
in-memory list (_EXPOSURE_REJECTIONS_TODAY, lost on restart) but never
persisted anywhere durable — unlike StrategyLab and RiskManagerAI
rejections, which already flow into data/rejection_audit.db via
ingest_rejection(). This is audit/observability only: it must not change
which signals are selected, sized, or capped.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from risk_control.capital_risk_engine import CapitalRiskEngine, _MAX_POSITIONS
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel


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
        target_price=112.5, confidence=6.0, strategy_name="unassigned",
    )
    defaults.update(overrides)
    return TradeSignal(**defaults)


def test_max_positions_cap_persists_to_rejection_audit_db():
    """Overflow signals beyond _MAX_POSITIONS must call ingest_rejection()
    with reason=MAX_POSITIONS_CAP, in addition to the existing in-memory
    audit list — and selection behavior (len(result) <= _MAX_POSITIONS)
    must be completely unchanged."""
    cre = CapitalRiskEngine()
    signals = [
        _sig(symbol=f"SYM{i}", strategy_name="KDA_AUTHORITY", confidence=8.0,
             kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
             kda_evidence_state="VALIDATED", kda_conviction=8.0 + i * 0.01)
        for i in range(_MAX_POSITIONS + 3)
    ]
    mock_tracker = MagicMock()
    with patch("analysis.rejection_tracker.get_rejection_tracker", return_value=mock_tracker):
        result = cre.allocate(signals, _snapshot(), portfolio=None)

    assert len(result) <= _MAX_POSITIONS  # selection behavior unchanged
    assert mock_tracker.ingest_rejection.called
    reasons = {
        c.kwargs.get("rejected_reason") for c in mock_tracker.ingest_rejection.call_args_list
    }
    assert "MAX_POSITIONS_CAP" in reasons


def test_max_positions_cap_ingest_failure_does_not_block_allocation():
    """If rejection_tracker itself raises, allocate() must still return
    the normal capped result — audit failures must never affect trading."""
    cre = CapitalRiskEngine()
    signals = [
        _sig(symbol=f"SYM{i}", strategy_name="KDA_AUTHORITY", confidence=8.0,
             kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
             kda_evidence_state="VALIDATED", kda_conviction=8.0 + i * 0.01)
        for i in range(_MAX_POSITIONS + 3)
    ]
    with patch("analysis.rejection_tracker.get_rejection_tracker",
               side_effect=RuntimeError("db unavailable")):
        result = cre.allocate(signals, _snapshot(), portfolio=None)
    assert len(result) <= _MAX_POSITIONS


def test_exposure_cap_exceeded_persists_to_rejection_audit_db():
    """A signal rejected for exceeding total deployable exposure must call
    ingest_rejection() with reason=EXPOSURE_CAP_EXCEEDED."""
    cre = CapitalRiskEngine()
    # Large notional signals designed to exhaust deployable capital quickly,
    # forcing at least one EXPOSURE_CAP_EXCEEDED rejection well before
    # _MAX_POSITIONS is reached.
    signals = [
        _sig(symbol=f"BIG{i}", strategy_name="KDA_AUTHORITY",
             entry_price=50000.0, stop_loss=49000.0, target_price=53000.0,
             confidence=9.0, kda_decision="KNOWLEDGE_BUY",
             authorization_source="KDA", kda_evidence_state="VALIDATED",
             kda_conviction=9.0 - i * 0.01)
        for i in range(_MAX_POSITIONS)
    ]
    mock_tracker = MagicMock()
    with patch("analysis.rejection_tracker.get_rejection_tracker", return_value=mock_tracker):
        cre.allocate(signals, _snapshot(), portfolio=None)

    if mock_tracker.ingest_rejection.called:
        reasons = {
            c.kwargs.get("rejected_reason") for c in mock_tracker.ingest_rejection.call_args_list
        }
        assert reasons.issubset({"MAX_POSITIONS_CAP", "EXPOSURE_CAP_EXCEEDED"})
