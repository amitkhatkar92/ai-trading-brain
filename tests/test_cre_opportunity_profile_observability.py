"""
CRE opportunity-profile observability tests.

These tests verify metadata capture only; CRE ranking, sizing, and rejection
behavior remain covered by the existing CRE integration tests.
"""
from __future__ import annotations

from models.trade_signal import SignalDirection, TradeSignal
from risk_control.capital_risk_engine import CapitalRiskEngine


def test_cre_records_available_scanner_and_kda_fields():
    signal = TradeSignal(
        symbol="TATASTEEL",
        direction=SignalDirection.BUY,
        confidence=5.3,
        scanner_score=5.3,
        kda_conviction=8.1,
        knowledge_authority_score=0.86,
        kda_evidence_state="VALIDATED",
        kda_target=180.0,
        kda_stop=165.0,
        kda_horizon_p50=3,
    )

    metadata = CapitalRiskEngine._opportunity_profile_metadata(signal)

    assert metadata == {
        "scanner_score": 5.3,
        "kda_conviction": 8.1,
        "knowledge_authority_score": 0.86,
        "kda_evidence_state": "VALIDATED",
        "kda_target": 180.0,
        "kda_stop": 165.0,
        "kda_horizon_p50": 3,
    }


def test_cre_observability_handles_missing_kda_fields():
    signal = TradeSignal(symbol="INFY", direction=SignalDirection.BUY, confidence=5.5)

    metadata = CapitalRiskEngine._opportunity_profile_metadata(signal)

    assert metadata["scanner_score"] == 0.0
    assert metadata["kda_conviction"] is None
    assert metadata["knowledge_authority_score"] is None
    assert metadata["kda_evidence_state"] is None
    assert metadata["kda_target"] is None
    assert metadata["kda_stop"] is None
    assert metadata["kda_horizon_p50"] is None


def test_cre_sizing_ignores_observability_fields():
    engine = CapitalRiskEngine()
    legacy_signal = TradeSignal(
        symbol="RELIANCE",
        direction=SignalDirection.BUY,
        confidence=5.3,
        entry_price=100.0,
        stop_loss=98.0,
        target_price=105.0,
    )
    profiled_signal = TradeSignal(
        symbol="RELIANCE",
        direction=SignalDirection.BUY,
        confidence=5.3,
        scanner_score=5.3,
        kda_conviction=8.7,
        knowledge_authority_score=0.91,
        kda_evidence_state="DECISION_ELIGIBLE",
        kda_target=105.0,
        kda_stop=98.0,
        kda_horizon_p50=3,
        entry_price=100.0,
        stop_loss=98.0,
        target_price=105.0,
    )

    assert engine._size_position(legacy_signal, 100_000.0) == engine._size_position(
        profiled_signal, 100_000.0
    )
