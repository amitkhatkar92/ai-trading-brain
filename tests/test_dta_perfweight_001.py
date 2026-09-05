"""
DTA-PERFWEIGHT-001 — PortfolioAllocationAI perf_weight KDA-authority boundary.

Calls the real PortfolioAllocationAI._size() method directly (production
code, not a simulation), with a fake StrategyPerformanceTracker injected via
monkeypatch, to verify:

  1. KDA-authoritative + strong strategy history -> quantity unchanged.
  2. KDA-authoritative + weak strategy history -> quantity unchanged.
  3. BOTH + strong StrategyLab history -> quantity unchanged (closes the
     StrategyLab-identity leak).
  4. KDA-only ("KDA_AUTHORITY" label) -> quantity unchanged.
  5. DTA-KDA-AUTHORITY-WIDEN-001: USEFUL evidence now bypasses perf_weight
     too (tracker never called) -- evidence_state no longer gates authority.
  6. Non-KDA -> existing perf_weight STILL applies (regression).
  7. Strategy name cannot alter KDA-authoritative sizing: same signal, two
     different strategy_name values with different hypothetical weights
     -> identical final quantity.
  8. For KDA-authoritative signals, the tracker's get_performance_weight()
     is NEVER CALLED AT ALL (call count == 0) -- not called-then-ignored.
"""
from __future__ import annotations

from datetime import datetime

import risk_control.portfolio_allocation_ai as pa_module
from risk_control.portfolio_allocation_ai import PortfolioAllocationAI
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel


class _FakeTracker:
    """Records every call and returns a fixed, controllable weight."""
    def __init__(self, weight: float = 1.0):
        self.weight = weight
        self.calls: list[str] = []

    def get_performance_weight(self, strategy_name: str) -> float:
        self.calls.append(strategy_name)
        return self.weight


def _patch_tracker(monkeypatch, weight: float = 1.0) -> _FakeTracker:
    fake = _FakeTracker(weight)
    monkeypatch.setattr(pa_module, "get_performance_tracker", lambda: fake)
    return fake


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


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        timestamp=datetime.now(), indices={},
        regime=RegimeLabel.RANGE_MARKET, volatility=VolatilityLevel.MEDIUM,
        vix=15.0, pcr=1.0, market_breadth=0.5,
    )


_KDA_ONLY = dict(
    strategy_name="KDA_AUTHORITY",
    kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
    kda_evidence_state="VALIDATED", kda_conviction=8.0,
)
_BOTH = dict(
    strategy_name="Momentum_Retest",
    kda_decision="KNOWLEDGE_BUY", authorization_source="BOTH",
    kda_evidence_state="DECISION_ELIGIBLE", kda_conviction=8.5,
)


def test_kda_authoritative_strong_history_quantity_unchanged(monkeypatch):
    pa = PortfolioAllocationAI()
    sig = _sig(**_KDA_ONLY)
    _patch_tracker(monkeypatch, weight=1.0)
    baseline = pa._size(sig, _snapshot())
    _patch_tracker(monkeypatch, weight=2.0)   # would double qty if not bypassed
    weighted = pa._size(_sig(**_KDA_ONLY), _snapshot())
    assert baseline is not None and weighted is not None
    assert baseline.quantity == weighted.quantity


def test_kda_authoritative_weak_history_quantity_unchanged(monkeypatch):
    pa = PortfolioAllocationAI()
    _patch_tracker(monkeypatch, weight=1.0)
    baseline = pa._size(_sig(**_KDA_ONLY), _snapshot())
    _patch_tracker(monkeypatch, weight=0.5)   # would halve qty if not bypassed
    weighted = pa._size(_sig(**_KDA_ONLY), _snapshot())
    assert baseline is not None and weighted is not None
    assert baseline.quantity == weighted.quantity


def test_both_strong_stratlab_history_quantity_unchanged(monkeypatch):
    pa = PortfolioAllocationAI()
    _patch_tracker(monkeypatch, weight=1.0)
    baseline = pa._size(_sig(**_BOTH), _snapshot())
    _patch_tracker(monkeypatch, weight=2.0)
    weighted = pa._size(_sig(**_BOTH), _snapshot())
    assert baseline is not None and weighted is not None
    assert baseline.quantity == weighted.quantity


def test_kda_only_label_quantity_unchanged(monkeypatch):
    pa = PortfolioAllocationAI()
    _patch_tracker(monkeypatch, weight=1.0)
    baseline = pa._size(_sig(**_KDA_ONLY), _snapshot())
    _patch_tracker(monkeypatch, weight=1.7)
    weighted = pa._size(_sig(**_KDA_ONLY), _snapshot())
    assert baseline is not None and weighted is not None
    assert baseline.quantity == weighted.quantity


def test_kda_useful_evidence_now_bypasses_perf_weight(monkeypatch):
    """DTA-KDA-AUTHORITY-WIDEN-001: USEFUL evidence (kda_decision BUY,
    authorization_source KDA) is now KDA-authoritative too -- perf_weight
    is bypassed exactly like VALIDATED/DECISION_ELIGIBLE, and the tracker
    is never called."""
    pa = PortfolioAllocationAI()
    sig_common = dict(
        strategy_name="KDA_AUTHORITY", confidence=6.5,
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="USEFUL", kda_conviction=None,
    )
    fake = _patch_tracker(monkeypatch, weight=1.0)
    baseline = pa._size(_sig(**sig_common), _snapshot())
    fake2 = _patch_tracker(monkeypatch, weight=2.0)
    weighted = pa._size(_sig(**sig_common), _snapshot())
    assert baseline is not None and weighted is not None
    assert weighted.quantity == baseline.quantity
    assert fake.calls == [] and fake2.calls == []


def test_non_kda_still_uses_existing_perf_weight(monkeypatch):
    """Regression: ordinary non-KDA signal -> perf_weight still applies
    exactly as before."""
    pa = PortfolioAllocationAI()
    sig_common = dict(strategy_name="Mean_Reversion_RSI_HiVol", confidence=7.0)
    _patch_tracker(monkeypatch, weight=1.0)
    baseline = pa._size(_sig(**sig_common), _snapshot())
    _patch_tracker(monkeypatch, weight=0.5)
    weighted = pa._size(_sig(**sig_common), _snapshot())
    assert baseline is not None and weighted is not None
    assert weighted.quantity != baseline.quantity
    assert weighted.quantity == max(1, int(baseline.quantity * 0.5))


def test_strategy_name_cannot_alter_kda_authoritative_sizing(monkeypatch):
    """T7 (strongest test): same KDA-authoritative opportunity, two
    different strategy_name values, each hypothetically mapped to a
    DIFFERENT performance weight -> identical final quantity."""
    pa = PortfolioAllocationAI()
    common = dict(
        kda_decision="KNOWLEDGE_BUY", authorization_source="BOTH",
        kda_evidence_state="VALIDATED", kda_conviction=8.0,
    )
    fake_a = _FakeTracker(weight=2.0)   # "KDA_AUTHORITY" would get 2.0x
    monkeypatch.setattr(pa_module, "get_performance_tracker", lambda: fake_a)
    out_a = pa._size(_sig(strategy_name="KDA_AUTHORITY", **common), _snapshot())

    fake_b = _FakeTracker(weight=0.5)   # "Momentum_Retest" would get 0.5x
    monkeypatch.setattr(pa_module, "get_performance_tracker", lambda: fake_b)
    out_b = pa._size(_sig(strategy_name="Momentum_Retest", **common), _snapshot())

    assert out_a is not None and out_b is not None
    assert out_a.quantity == out_b.quantity


def test_tracker_never_called_for_kda_authoritative(monkeypatch):
    """Explicit call-count assertion: the tracker function must not be
    called AT ALL for KDA-authoritative signals — not called-then-
    overridden, not called-then-ignored."""
    pa = PortfolioAllocationAI()
    fake = _patch_tracker(monkeypatch, weight=1.0)
    pa._size(_sig(**_KDA_ONLY), _snapshot())
    assert fake.calls == []

    fake_both = _patch_tracker(monkeypatch, weight=1.0)
    pa._size(_sig(**_BOTH), _snapshot())
    assert fake_both.calls == []

    # Regression: non-KDA and weak/partial KDA DO still call it.
    fake_non_kda = _patch_tracker(monkeypatch, weight=1.0)
    pa._size(_sig(strategy_name="Mean_Reversion_RSI_HiVol", confidence=7.0), _snapshot())
    assert fake_non_kda.calls == ["Mean_Reversion_RSI_HiVol"]
