"""
CRE ranking migration tests.

These tests cover ranking ownership only. Risk sizing, caps, and exposure
constraints remain unchanged and are exercised through CapitalRiskEngine.allocate.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from models.market_data import RegimeLabel
from models.trade_signal import SignalDirection, TradeSignal
from risk_control import capital_risk_engine as cre_module
from risk_control.capital_risk_engine import CapitalRiskEngine


def _snapshot():
    return SimpleNamespace(regime=SimpleNamespace(value=RegimeLabel.BULL_TREND.value), vix=14.0)


def _portfolio():
    return SimpleNamespace(positions={}, drawdown_pct=0.0)


def _signal(symbol, confidence, *, kda=None, source=None, target=110.0, stop=90.0, qualified=False):
    signal = TradeSignal(
        symbol=symbol,
        direction=SignalDirection.BUY,
        confidence=confidence,
        entry_price=100.0,
        stop_loss=stop,
        target_price=target,
        quantity=1,
        strategy_name="Mean_Reversion",
        kda_decision="KNOWLEDGE_BUY" if kda is not None or qualified else None,
        kda_conviction=kda,
        authorization_source=source,
    )
    return signal


def _allocate_one(monkeypatch, signals):
    monkeypatch.setattr(cre_module, "_MAX_POSITIONS", 1)
    engine = CapitalRiskEngine()
    monkeypatch.setattr(engine, "_size_position", lambda signal, budget: 1)
    return engine.allocate(signals, _snapshot(), _portfolio())


def test_kda_qualified_ranking_uses_kda_conviction(monkeypatch):
    legacy_high = _signal("LEGACY_HIGH", 6.0, target=105.0)
    kda_high = _signal("KDA_HIGH", 5.0, kda=9.0, source="KDA", target=105.0)

    result = _allocate_one(monkeypatch, [legacy_high, kda_high])

    assert len(result) == 1
    assert result[0].symbol == "KDA_HIGH"


def test_legacy_candidate_ranking_uses_legacy_confidence(monkeypatch):
    legacy_high = _signal("LEGACY_HIGH", 9.0, target=105.0)
    legacy_low = _signal("LEGACY_LOW", 5.0, target=105.0)

    result = _allocate_one(monkeypatch, [legacy_low, legacy_high])

    assert len(result) == 1
    assert result[0].symbol == "LEGACY_HIGH"


def test_kda_conviction_missing_uses_neutral_intelligence_score(monkeypatch):
    fallback_high = _signal("FALLBACK_HIGH", 8.0, source="KDA", qualified=True, target=105.0)
    fallback_low = _signal("FALLBACK_LOW", 5.0, source="KDA", qualified=True, target=105.0)

    result = _allocate_one(monkeypatch, [fallback_low, fallback_high])

    assert len(result) == 1
    assert result[0].symbol == "FALLBACK_LOW"

    # Legacy confidence must not determine the intelligence component here.


def test_rr_component_remains_part_of_ranking(monkeypatch):
    lower_rr = _signal("LOW_RR", 8.0, kda=8.0, source="KDA", target=105.0)
    higher_rr = _signal("HIGH_RR", 8.0, kda=8.0, source="KDA", target=115.0)

    result = _allocate_one(monkeypatch, [lower_rr, higher_rr])

    assert len(result) == 1
    assert result[0].symbol == "HIGH_RR"


def test_max_positions_behavior_remains_one(monkeypatch):
    signals = [
        _signal("ONE", 8.0, kda=8.0, source="KDA"),
        _signal("TWO", 7.0, kda=7.0, source="KDA"),
    ]

    result = _allocate_one(monkeypatch, signals)

    assert len(result) <= 1
