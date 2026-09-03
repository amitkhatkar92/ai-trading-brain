"""
DTA-SIZING-AUTHORITY-001 — PortfolioAllocationAI sizing intelligence input
for KDA-authoritative candidates.

Calls the real PortfolioAllocationAI._size() method directly (production
code, not a simulation) to verify:
  1. KDA-authoritative uses kda_conviction/10 as the intelligence input,
     not legacy confidence.
  2. KDA-authoritative + missing kda_conviction -> neutral 0.0, NEVER
     falls back to legacy confidence.
  3. Non-KDA-authoritative signals are completely unchanged (both the
     normal confidence path and the confidence<=0 fallback-to-0.7 path).
  4. KDA USEFUL/DEVELOPING evidence (not VALIDATED/DECISION_ELIGIBLE) is
     NOT exempted -- still uses legacy confidence.
  5. Partial KDA-authoritative matches (missing one of the three required
     conditions) do not trigger the KDA path.
  6. bucket_capital / caps / perf_weight machinery is untouched --
     downstream caps still apply identically regardless of which
     intelligence input was used.
"""
from __future__ import annotations

from datetime import datetime

from risk_control.portfolio_allocation_ai import PortfolioAllocationAI
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from config import TOTAL_CAPITAL, MAX_RISK_PER_TRADE_PCT, ALLOCATION


def _sig(**overrides) -> TradeSignal:
    defaults = dict(
        symbol="TESTSTOCK",   # not in LARGE_CAP/MID_CAP lists -> small_cap bucket
        direction=SignalDirection.BUY,
        signal_type=SignalType.EQUITY,
        entry_price=100.0,
        stop_loss=95.0,        # stop distance = 5.0
        target_price=112.5,
        confidence=6.0,
    )
    defaults.update(overrides)
    return TradeSignal(**defaults)


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        timestamp=datetime.now(), indices={},
        regime=RegimeLabel.RANGE_MARKET,
        volatility=VolatilityLevel.MEDIUM,
        vix=15.0, pcr=1.0, market_breadth=0.5,
    )


def _pa() -> PortfolioAllocationAI:
    return PortfolioAllocationAI()


def _expected_qty(conf_norm: float, entry: float = 100.0, stop: float = 95.0) -> int:
    """Reproduce the canonical formula for assertion (not a separate
    implementation of the gating logic -- just the arithmetic)."""
    risk_pct = MAX_RISK_PER_TRADE_PCT * (0.6 + conf_norm * 0.8)
    risk_amount = TOTAL_CAPITAL * risk_pct
    return int(risk_amount / abs(entry - stop))


def test_kda_authoritative_uses_kda_conviction_not_confidence():
    """T1: KDA-authoritative signal is sized from kda_conviction/10, not confidence."""
    pa = _pa()
    sig = _sig(
        confidence=1.0,   # deliberately low/irrelevant legacy confidence
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED", kda_conviction=10.0,
    )
    out = pa._size(sig, _snapshot())
    assert out is not None
    assert out.quantity == _expected_qty(1.0)  # conf_norm from kda_conviction=10 -> 1.0
    assert out.quantity != _expected_qty(0.1)  # would be the value if confidence=1.0 governed


def test_kda_authoritative_missing_conviction_is_neutral_not_confidence_fallback():
    """T2: KDA-authoritative + kda_conviction=None -> neutral 0.0, never legacy confidence."""
    pa = _pa()
    sig = _sig(
        confidence=9.0,   # deliberately high legacy confidence
        kda_decision="KNOWLEDGE_SELL", authorization_source="BOTH",
        kda_evidence_state="DECISION_ELIGIBLE", kda_conviction=None,
    )
    out = pa._size(sig, _snapshot())
    assert out is not None
    assert out.quantity == _expected_qty(0.0)   # neutral, NOT confidence=9.0 -> 0.9


def test_non_kda_authoritative_uses_confidence_unchanged():
    """T3: Non-KDA signal sizing is completely unchanged (existing formula)."""
    pa = _pa()
    sig = _sig(confidence=6.0)  # no KDA fields at all
    out = pa._size(sig, _snapshot())
    assert out is not None
    assert out.quantity == _expected_qty(0.6)


def test_non_kda_zero_confidence_fallback_unchanged():
    """T3b: Non-KDA + confidence<=0 -> existing 0.7 fallback preserved."""
    pa = _pa()
    sig = _sig(confidence=0.0)
    out = pa._size(sig, _snapshot())
    assert out is not None
    assert out.quantity == _expected_qty(0.7)


def test_kda_useful_evidence_not_exempted_uses_confidence():
    """T4: KDA USEFUL evidence (not VALIDATED/DECISION_ELIGIBLE) still uses confidence."""
    pa = _pa()
    sig = _sig(
        confidence=6.0,
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="USEFUL", kda_conviction=9.0,
    )
    out = pa._size(sig, _snapshot())
    assert out is not None
    assert out.quantity == _expected_qty(0.6)   # confidence-based, kda_conviction ignored


def test_kda_developing_evidence_not_exempted_uses_confidence():
    """T4b: KDA DEVELOPING evidence -> still uses confidence."""
    pa = _pa()
    sig = _sig(
        confidence=6.0,
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="DEVELOPING", kda_conviction=9.0,
    )
    out = pa._size(sig, _snapshot())
    assert out is not None
    assert out.quantity == _expected_qty(0.6)


def test_kda_authoritative_requires_full_combination_partial_matches_use_confidence():
    """T5: partial KDA-authoritative matches (missing one of the three required
    conditions) fall back to the legacy confidence path, not kda_conviction."""
    pa = _pa()

    # Missing authorization_source
    sig_a = _sig(confidence=6.0, kda_decision="KNOWLEDGE_BUY",
                 authorization_source=None, kda_evidence_state="VALIDATED",
                 kda_conviction=9.0)
    out_a = pa._size(sig_a, _snapshot())
    assert out_a.quantity == _expected_qty(0.6)

    # kda_decision is KNOWLEDGE_WAIT, not BUY/SELL
    sig_b = _sig(confidence=6.0, kda_decision="KNOWLEDGE_WAIT",
                 authorization_source="KDA", kda_evidence_state="VALIDATED",
                 kda_conviction=9.0)
    out_b = pa._size(sig_b, _snapshot())
    assert out_b.quantity == _expected_qty(0.6)

    # authorization_source is STRATEGY_LAB, not KDA/BOTH
    sig_c = _sig(confidence=6.0, kda_decision="KNOWLEDGE_BUY",
                 authorization_source="STRATEGY_LAB", kda_evidence_state="VALIDATED",
                 kda_conviction=9.0)
    out_c = pa._size(sig_c, _snapshot())
    assert out_c.quantity == _expected_qty(0.6)


def test_bucket_cap_still_applies_to_kda_authoritative_sizing():
    """T6: downstream bucket-capital cap still binds identically regardless
    of which intelligence input produced the pre-cap quantity."""
    pa = _pa()
    # Tight stop distance -> large pre-cap qty that should get capped by the
    # small-cap bucket allocation (15% of TOTAL_CAPITAL / entry_price).
    sig = _sig(
        confidence=1.0, entry_price=100.0, stop_loss=99.9,  # stop distance = 0.1
        kda_decision="KNOWLEDGE_BUY", authorization_source="KDA",
        kda_evidence_state="VALIDATED", kda_conviction=10.0,
    )
    out = pa._size(sig, _snapshot())
    assert out is not None
    max_qty_by_bucket = int((TOTAL_CAPITAL * ALLOCATION["small_cap"]) / sig.entry_price)
    assert out.quantity == max_qty_by_bucket
