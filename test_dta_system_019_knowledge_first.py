"""
test_dta_system_019_knowledge_first.py
=========================================
DTA-SYSTEM-019 — Knowledge-First Architecture: adversarial tests for the
removal of pre-KDA strategy gates from _identify_setup().

Root cause being tested:
  Previously, 6 reason codes in _identify_setup() returned (None, reason_code)
  before the signal ever reached KDA.  Stocks like KPITTECH (RSI 47, bull trend,
  vol_ratio 0.49) were blocked by "bull_gate" and never received knowledge
  evaluation despite 408 KEL entries and +3.29% Friday performance.

Fix (DTA-SYSTEM-019):
  All non-safety rejections now return a TradeSignal with
  strategy_name="knowledge_referred" so every data-quality-passing candidate
  reaches KDA for evidence-based evaluation.

Safety invariants verified:
  - high_atr gate remains (data quality)
  - bear_market gate remains (hard regime safety)
  - knowledge_referred signal has valid price geometry (target > entry > stop)
  - KDA authority preserved (KNOWLEDGE_WAIT blocks execution downstream)
  - CRE/RiskGuardian remain mandatory veto layers (unchanged)
  - opportunity_id lineage assignment is not affected

Test inventory (T001–T015):
  T001  bull_gate → knowledge_referred (primary fix: KPITTECH / TECHM scenario)
  T002  rsi_neutral → knowledge_referred (primary fix: RSI 47 mid-range stock)
  T003  breakout_vol_low → knowledge_referred (breakout with low volume)
  T004  breakout_rsi_hi → knowledge_referred (breakout but RSI too hot)
  T005  retest_rsi_oob → knowledge_referred (retest zone, RSI outside 50-65)
  T006  bounce_price_hi → knowledge_referred (oversold but price above support)
  T007  high_atr → None (data quality gate preserved)
  T008  bear_market → None (safety gate preserved)
  T009  clean breakout match → signal_found (existing setups still work)
  T010  trend_pullback match → signal_found (existing setups still work)
  T011  mean_reversion_bounce match → signal_found (existing setups still work)
  T012  knowledge_referred geometry invariant: target > entry > stop > 0
  T013  knowledge_referred strategy_name is exactly "knowledge_referred"
  T014  knowledge_referred notes contains scanner_context label
  T015  knowledge_referred confidence: 5.0 ≤ conf ≤ 6.5
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

# ── path bootstrap ─────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── minimal test harness ───────────────────────────────────────────────────────
_PASS = 0
_FAIL = 0


def _ok(tid: str, desc: str) -> None:
    global _PASS
    _PASS += 1
    print(f"  PASS  {tid}: {desc}")


def _fail(tid: str, desc: str, reason: str) -> None:
    global _FAIL
    _FAIL += 1
    print(f"  FAIL  {tid}: {desc}")
    print(f"         Reason: {reason}")


def _assert(tid: str, desc: str, cond: bool, reason: str = "") -> None:
    if cond:
        _ok(tid, desc)
    else:
        _fail(tid, desc, reason or "assertion failed")


# ══════════════════════════════════════════════════════════════════════════════
# Minimal stubs — avoid importing live broker / feed dependencies
# ══════════════════════════════════════════════════════════════════════════════

class RegimeLabel(str, Enum):
    BULL_TREND   = "BULL_TREND"
    BULL_NORMAL  = "BULL_NORMAL"
    RANGE_BOUND  = "RANGE_BOUND"
    BEAR_MARKET  = "BEAR_MARKET"
    VOLATILE     = "VOLATILE"
    UNKNOWN      = "UNKNOWN"


@dataclass
class _Snapshot:
    regime: RegimeLabel = RegimeLabel.BULL_NORMAL
    vix: float = 14.5


def _stock(
    symbol: str = "TESTSTOCK",
    ltp: float = 500.0,
    support: float = 450.0,
    resistance: float = 550.0,
    rsi: float = 50.0,
    volume_ratio: float = 1.5,
    adv_crore: float = 20.0,
    atr: float = 0.0,    # 0 = let scanner compute from S/R spread
) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "symbol": symbol,
        "ltp": ltp,
        "support": support,
        "resistance": resistance,
        "rsi": rsi,
        "volume_ratio": volume_ratio,
        "adv_crore": adv_crore,
    }
    if atr:
        d["atr"] = atr
    return d


# ══════════════════════════════════════════════════════════════════════════════
# Import the function under test
# ══════════════════════════════════════════════════════════════════════════════

# We instantiate EquityScannerAI with heavy IO mocked out so that only
# _identify_setup() and _build_knowledge_referred_signal() are exercised.

from unittest.mock import patch

with patch("opportunity_engine.equity_scanner_ai.get_logger", return_value=MagicMock()):
    with patch("opportunity_engine.equity_scanner_ai.Path", MagicMock()):
        from opportunity_engine.equity_scanner_ai import EquityScannerAI  # type: ignore

scanner = EquityScannerAI()


def _call(stock_kw: Dict[str, Any], regime: RegimeLabel = RegimeLabel.BULL_NORMAL,
          vol_ratio_min: float = 2.0):
    """Call _identify_setup and return (sig, reason)."""
    snap = _Snapshot(regime=regime)
    # Patch the RegimeLabel in the module to match our stub
    import opportunity_engine.equity_scanner_ai as _esm
    orig_regime = _esm.RegimeLabel
    _esm.RegimeLabel = RegimeLabel   # type: ignore
    try:
        sig, reason = scanner._identify_setup(stock_kw, snap, vol_ratio_min=vol_ratio_min)
    finally:
        _esm.RegimeLabel = orig_regime
    return sig, reason


# ══════════════════════════════════════════════════════════════════════════════
# T001: bull_gate → knowledge_referred
# Scenario: KPITTECH equivalent — BULL_TREND, RSI 47, vol_ratio 0.49, price
# in support zone (ltp=490, support=475 → 490/475=1.03 ∈ [0.97,1.04]) but
# vol_ratio 0.49 < 1.2 minimum for trend_pullback.
# ATR check: spread=35, atr=14, atr_pct=14/490=2.86% < 4.0% ✓
# ══════════════════════════════════════════════════════════════════════════════
def t001():
    tid = "T001"
    desc = "bull_gate → knowledge_referred (KPITTECH/TECHM scenario)"
    st = _stock("KPITTECH", ltp=490.0, support=475.0, resistance=510.0,
                rsi=47.0, volume_ratio=0.49)
    sig, reason = _call(st, regime=RegimeLabel.BULL_TREND, vol_ratio_min=2.0)
    _assert(tid, desc, sig is not None and reason == "knowledge_referred",
            f"Expected knowledge_referred, got sig={sig}, reason={reason}")


# ══════════════════════════════════════════════════════════════════════════════
# T002: rsi_neutral → knowledge_referred
# Scenario: RSI 50, price mid-range — RANGE_BOUND regime, no setup matches.
# ATR check: spread=35, atr=14, atr_pct=14/490=2.86% < 4.0% ✓
# ══════════════════════════════════════════════════════════════════════════════
def t002():
    tid = "T002"
    desc = "rsi_neutral → knowledge_referred (RSI 50, price mid-range)"
    # RANGE_BOUND, ltp=490 not in breakout/retest/bounce zones, rsi=53 → rsi_neutral
    st = _stock("TECHM", ltp=490.0, support=475.0, resistance=510.0,
                rsi=53.0, volume_ratio=0.8)
    sig, reason = _call(st, regime=RegimeLabel.RANGE_BOUND)
    _assert(tid, desc, sig is not None and reason == "knowledge_referred",
            f"Expected knowledge_referred, got sig={sig}, reason={reason}")


# ══════════════════════════════════════════════════════════════════════════════
# T003: breakout_vol_low → knowledge_referred
# Scenario: ltp > resistance but vol_ratio < vol_ratio_min=2.0.
# ATR check: spread=35, atr=14, atr_pct=14/515=2.72% < 4.0% ✓
# ══════════════════════════════════════════════════════════════════════════════
def t003():
    tid = "T003"
    desc = "breakout_vol_low → knowledge_referred (low-volume breakout)"
    # ltp=515 > resistance=510, vol_ratio=1.2 < 2.0 → was "breakout_vol_low"
    st = _stock("ELGIEQUIP", ltp=515.0, support=475.0, resistance=510.0,
                rsi=58.0, volume_ratio=1.2)
    sig, reason = _call(st, regime=RegimeLabel.BULL_NORMAL, vol_ratio_min=2.0)
    _assert(tid, desc, sig is not None and reason == "knowledge_referred",
            f"Expected knowledge_referred, got sig={sig}, reason={reason}")


# ══════════════════════════════════════════════════════════════════════════════
# T004: breakout_rsi_hi → knowledge_referred
# Scenario: ltp > resistance, vol_ratio >= 2.0, BUT rsi >= 75.
# ATR check: spread=35, atr=14, atr_pct=14/515=2.72% < 4.0% ✓
# ══════════════════════════════════════════════════════════════════════════════
def t004():
    tid = "T004"
    desc = "breakout_rsi_hi → knowledge_referred (breakout, rsi=76 overbought)"
    # ltp=515 > resistance=510, vol_ratio=2.5 ≥ 2.0 BUT rsi=76 ≥ 75 → was "breakout_rsi_hi"
    st = _stock("PERSISTENT", ltp=515.0, support=475.0, resistance=510.0,
                rsi=76.0, volume_ratio=2.5)
    sig, reason = _call(st, regime=RegimeLabel.BULL_NORMAL, vol_ratio_min=2.0)
    _assert(tid, desc, sig is not None and reason == "knowledge_referred",
            f"Expected knowledge_referred, got sig={sig}, reason={reason}")


# ══════════════════════════════════════════════════════════════════════════════
# T005: retest_rsi_oob → knowledge_referred
# Scenario: ltp inside resistance retest zone [res*0.995, res*1.01] but RSI outside 50-65.
# ATR check: spread=35, atr=14, atr_pct=14/508=2.76% < 4.0% ✓
# ══════════════════════════════════════════════════════════════════════════════
def t005():
    tid = "T005"
    desc = "retest_rsi_oob → knowledge_referred (retest zone, RSI=42)"
    # resistance=510, retest zone=[507.45, 515.1].  ltp=508 ∈ zone, RSI=42 < 50 → was "retest_rsi_oob"
    st = _stock("HAVELLS", ltp=508.0, support=475.0, resistance=510.0,
                rsi=42.0, volume_ratio=1.0)
    sig, reason = _call(st, regime=RegimeLabel.RANGE_BOUND)
    _assert(tid, desc, sig is not None and reason == "knowledge_referred",
            f"Expected knowledge_referred, got sig={sig}, reason={reason}")


# ══════════════════════════════════════════════════════════════════════════════
# T006: bounce_price_hi → knowledge_referred
# Scenario: RSI <= 45 (oversold) but ltp > support * 1.02.
# ATR check: spread=35, atr=14, atr_pct=14/487=2.87% < 4.0% ✓
# ══════════════════════════════════════════════════════════════════════════════
def t006():
    tid = "T006"
    desc = "bounce_price_hi → knowledge_referred (oversold RSI, price above support)"
    # support=475, ltp=487 = support*1.025 > 1.02, RSI=38 ≤ 45 → was "bounce_price_hi"
    st = _stock("TATASTEEL", ltp=487.0, support=475.0, resistance=510.0,
                rsi=38.0, volume_ratio=1.1)
    sig, reason = _call(st, regime=RegimeLabel.RANGE_BOUND)
    _assert(tid, desc, sig is not None and reason == "knowledge_referred",
            f"Expected knowledge_referred, got sig={sig}, reason={reason}")


# ══════════════════════════════════════════════════════════════════════════════
# T007: high_atr → None (data quality gate preserved)
# VOLATILITY_GUARD_ATR_PCT = 4.0%.  Need atr_pct > 4%.
# spread=200, atr=80, atr_pct=80/500=16% >> 4% ✓
# ══════════════════════════════════════════════════════════════════════════════
def t007():
    tid = "T007"
    desc = "high_atr → None (data quality gate preserved)"
    # Wide S/R spread → atr = (600-400)*0.4=80, atr_pct=80/500=16% > 4%
    st = _stock("NOISY", ltp=500.0, support=400.0, resistance=600.0,
                rsi=50.0, volume_ratio=1.0)
    sig, reason = _call(st, regime=RegimeLabel.BULL_NORMAL)
    _assert(tid, desc, sig is None and reason == "high_atr",
            f"Expected (None, 'high_atr'), got sig={sig}, reason={reason}")


# ══════════════════════════════════════════════════════════════════════════════
# T008: bear_market → None (safety gate preserved)
# ATR check: spread=35, atr=14, atr_pct=14/490=2.86% < 4% → passes ATR gate
# then hits bear_market gate ✓
# ══════════════════════════════════════════════════════════════════════════════
def t008():
    tid = "T008"
    desc = "bear_market → None (regime safety gate preserved)"
    st = _stock("RELIANCE", ltp=490.0, support=475.0, resistance=510.0,
                rsi=50.0, volume_ratio=2.5)
    sig, reason = _call(st, regime=RegimeLabel.BEAR_MARKET)
    _assert(tid, desc, sig is None and reason == "bear_market",
            f"Expected (None, 'bear_market'), got sig={sig}, reason={reason}")


# ══════════════════════════════════════════════════════════════════════════════
# T009: clean breakout → signal_found (existing setup intact)
# ATR: spread=35, atr=14, atr_pct=14/515=2.72% < 4% ✓
# ══════════════════════════════════════════════════════════════════════════════
def t009():
    tid = "T009"
    desc = "breakout → signal_found with strategy_name='breakout' (unchanged)"
    # ltp=515 > resistance=510, vol_ratio=2.5 ≥ 2.0, rsi=60 < 75 → Setup 1 matched
    st = _stock("INFY", ltp=515.0, support=475.0, resistance=510.0,
                rsi=60.0, volume_ratio=2.5)
    sig, reason = _call(st, regime=RegimeLabel.BULL_NORMAL, vol_ratio_min=2.0)
    _assert(tid, desc,
            sig is not None and reason == "signal_found" and sig.strategy_name == "breakout",
            f"Expected signal_found/breakout, got sig={sig}, reason={reason}")


# ══════════════════════════════════════════════════════════════════════════════
# T010: trend_pullback → signal_found (existing setup intact)
# support=475, ltp=490 ∈ [475*0.97=460.75, 475*1.04=494.0] ✓
# ATR: spread=35, atr=14, atr_pct=14/490=2.86% < 4% ✓
# ══════════════════════════════════════════════════════════════════════════════
def t010():
    tid = "T010"
    desc = "trend_pullback → signal_found with strategy_name='trend_pullback' (unchanged)"
    # BULL_TREND, ltp=490 in [460.75,494.0], RSI=45 ∈ [38,56], vol=1.3 ≥ 1.2 → trend_pullback
    st = _stock("TCS", ltp=490.0, support=475.0, resistance=510.0,
                rsi=45.0, volume_ratio=1.3)
    sig, reason = _call(st, regime=RegimeLabel.BULL_TREND)
    _assert(tid, desc,
            sig is not None and reason == "signal_found" and sig.strategy_name == "trend_pullback",
            f"Expected signal_found/trend_pullback, got sig={sig}, reason={reason}")


# ══════════════════════════════════════════════════════════════════════════════
# T011: mean_reversion_bounce → signal_found (existing setup intact)
# RSI=35 ≤ 45, ltp=480 ≤ support*1.02=484.5 → Setup 5 matched
# ATR: spread=35, atr=14, atr_pct=14/480=2.92% < 4% ✓
# ══════════════════════════════════════════════════════════════════════════════
def t011():
    tid = "T011"
    desc = "mean_reversion_bounce → signal_found (unchanged)"
    st = _stock("WIPRO", ltp=480.0, support=475.0, resistance=510.0,
                rsi=35.0, volume_ratio=1.0)
    sig, reason = _call(st, regime=RegimeLabel.RANGE_BOUND)
    _assert(tid, desc,
            sig is not None and reason == "signal_found" and sig.strategy_name == "mean_reversion_bounce",
            f"Expected signal_found/mean_reversion_bounce, got sig={sig}, reason={reason}")


# ══════════════════════════════════════════════════════════════════════════════
# T012: knowledge_referred price geometry invariant
# target > entry_price > stop_loss > 0 for all 6 context labels
# ══════════════════════════════════════════════════════════════════════════════
def t012():
    tid = "T012"
    desc = "knowledge_referred price geometry: target > entry > stop > 0 (all 6 contexts)"
    cases = [
        # (description, stock_kw, regime, vol_ratio_min)
        # All use tight spreads: atr_pct < 4% to pass ATR guard
        ("bull_gate",       _stock("S1", ltp=490, support=475, resistance=510, rsi=47, volume_ratio=0.49),
         RegimeLabel.BULL_TREND, 2.0),
        ("rsi_neutral",     _stock("S2", ltp=490, support=475, resistance=510, rsi=53, volume_ratio=0.8),
         RegimeLabel.RANGE_BOUND, 2.0),
        ("breakout_vol_low",_stock("S3", ltp=515, support=475, resistance=510, rsi=55, volume_ratio=1.2),
         RegimeLabel.BULL_NORMAL, 2.0),
        ("breakout_rsi_hi", _stock("S4", ltp=515, support=475, resistance=510, rsi=76, volume_ratio=2.5),
         RegimeLabel.BULL_NORMAL, 2.0),
        ("retest_rsi_oob",  _stock("S5", ltp=508, support=475, resistance=510, rsi=42, volume_ratio=1.0),
         RegimeLabel.RANGE_BOUND, 2.0),
        ("bounce_price_hi", _stock("S6", ltp=487, support=475, resistance=510, rsi=38, volume_ratio=1.1),
         RegimeLabel.RANGE_BOUND, 2.0),
    ]
    all_ok = True
    for label, st, regime, vrm in cases:
        sig, reason = _call(st, regime=regime, vol_ratio_min=vrm)
        if sig is None:
            _fail(tid, desc, f"{label}: sig is None (reason={reason})")
            all_ok = False
            continue
        ok = (sig.target_price > sig.entry_price > sig.stop_loss > 0)
        if not ok:
            _fail(tid, desc,
                  f"{label}: geometry violated: tp={sig.target_price} ep={sig.entry_price} sl={sig.stop_loss}")
            all_ok = False
    if all_ok:
        _ok(tid, desc)


# ══════════════════════════════════════════════════════════════════════════════
# T013: knowledge_referred strategy_name is exactly "knowledge_referred"
# ══════════════════════════════════════════════════════════════════════════════
def t013():
    tid = "T013"
    desc = "knowledge_referred strategy_name is exactly 'knowledge_referred'"
    st = _stock("CHECKSTRAT", ltp=490, support=475, resistance=510, rsi=50, volume_ratio=0.8)
    sig, reason = _call(st, regime=RegimeLabel.RANGE_BOUND)
    _assert(tid, desc,
            sig is not None and sig.strategy_name == "knowledge_referred",
            f"strategy_name={getattr(sig, 'strategy_name', None)}")


# ══════════════════════════════════════════════════════════════════════════════
# T014: knowledge_referred notes contains scanner_context label
# ══════════════════════════════════════════════════════════════════════════════
def t014():
    tid = "T014"
    desc = "knowledge_referred notes contains scanner_context label"
    # bull_gate scenario: ltp=490 in support zone, BULL_TREND, vol_ratio=0.49 < 1.2
    st = _stock("CTX", ltp=490, support=475, resistance=510, rsi=47, volume_ratio=0.49)
    sig, reason = _call(st, regime=RegimeLabel.BULL_TREND, vol_ratio_min=2.0)
    notes = getattr(sig, "notes", "") or ""
    _assert(tid, desc,
            "scanner_context:bull_gate" in notes,
            f"notes={notes!r}")


# ══════════════════════════════════════════════════════════════════════════════
# T015: knowledge_referred confidence is in [5.0, 6.5]
# ══════════════════════════════════════════════════════════════════════════════
def t015():
    tid = "T015"
    desc = "knowledge_referred confidence in [5.0, 6.5]"
    cases = [
        _stock("C1", ltp=490, support=475, resistance=510, rsi=50, volume_ratio=0.8),   # rsi_neutral
        _stock("C2", ltp=490, support=475, resistance=510, rsi=47, volume_ratio=0.49),  # bull_gate
        _stock("C3", ltp=515, support=475, resistance=510, rsi=55, volume_ratio=1.2),   # breakout_vol_low
        _stock("C4", ltp=490, support=475, resistance=510, rsi=65, volume_ratio=4.0),   # rsi_neutral high vol
    ]
    all_ok = True
    for st in cases:
        sig, reason = _call(st, regime=RegimeLabel.RANGE_BOUND, vol_ratio_min=2.0)
        if sig is None:
            continue  # might be high_atr etc. — skip
        if reason != "knowledge_referred":
            continue
        c = sig.confidence
        if not (5.0 <= c <= 6.5):
            _fail(tid, desc, f"{st['symbol']}: confidence={c} outside [5.0, 6.5]")
            all_ok = False
    if all_ok:
        _ok(tid, desc)


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("DTA-SYSTEM-019 Knowledge-First Architecture Tests")
    print("=" * 70)

    for fn in [t001, t002, t003, t004, t005, t006, t007, t008,
               t009, t010, t011, t012, t013, t014, t015]:
        try:
            fn()
        except Exception as exc:
            _fail(fn.__name__.upper(), f"{fn.__doc__ or fn.__name__}", str(exc))

    print("=" * 70)
    print(f"TOTAL: {_PASS + _FAIL}  PASS: {_PASS}  FAIL: {_FAIL}")
    print("=" * 70)
    if _FAIL:
        sys.exit(1)
