"""
tests/test_equity_hedge_shadow_readiness_001.py
==================================================
DTA-REALISTIC-THRESHOLDS-001: regression guard for
knowledge_system/equity_hedge_shadow_engine.py's MIN_OBS_AUTHENTICATED
recalibration (40 -> 10). Confirmed live 2026-10-05: evidence is scoped
PER SYMBOL, and real observations were spread across 18 different
symbols with the single most-observed symbol at only 6 in 20 days --
at that rate no symbol would ever realistically reach 40.

Coverage:
  - MIN_OBS_AUTHENTICATED == 10 (not 40) -- regression guard
  - MIN_OBS_AUTHENTICATED aligns with the pre-existing internal floor
    EQH-Ready-2's OOS split test already required (len(pnls) >= 10)
  - check_readiness(): a symbol with exactly 10 analysed, consistently
    profitable observations now correctly passes EQH-Ready-1 (volume)
  - a symbol with 9 observations still correctly fails EQH-Ready-1
"""
from __future__ import annotations

from unittest.mock import patch

import knowledge_system.equity_hedge_shadow_engine as engine


def _make_engine(tmp_path):
    persist_path = tmp_path / "equity_hedge_shadow_test.json"
    with patch.object(engine, "_PERSIST_PATH", str(persist_path)):
        eng = engine.EquityHedgeShadowEngine()
    return eng, persist_path


def _obs(symbol, i, pnl, chain_available=True, analysed=True):
    return engine.EquityHedgeShadowObservation(
        symbol=symbol,
        equity_order_id=f"ORD{i}",
        equity_direction="BUY",
        equity_entry_price=100.0,
        equity_qty=10,
        recorded_at=f"2026-09-{i+1:02d}T10:00:00",
        monitor_until=f"2026-09-{i+11:02d}",
        chain_available=chain_available,
        hedge_option_type="CE",
        hedge_strike=100.0,
        hedge_entry_premium=2.0,
        analysed=analysed,
        hypothetical_hedge_pnl=pnl,
        hedge_classification="HEDGE_WOULD_HAVE_HELPED" if pnl > 0 else "HEDGE_UNNECESSARY",
    )


def test_min_obs_authenticated_is_10_not_40():
    assert engine.MIN_OBS_AUTHENTICATED == 10


def test_min_obs_authenticated_aligns_with_oos_split_floor():
    """EQH-Ready-2's OOS sign test only ever runs when len(pnls) >= 10
    (hardcoded in check_readiness()) -- the volume gate should be at
    least that floor so Ready-1 passing actually gives Ready-2 a chance
    to run, instead of being stricter than Ready-2 could ever test for."""
    assert engine.MIN_OBS_AUTHENTICATED >= 10


def test_exactly_10_profitable_observations_passes_volume_gate(tmp_path):
    eng, _ = _make_engine(tmp_path)
    obs = [_obs("RELIANCE", i, pnl=5.0) for i in range(10)]
    with eng._lock:
        eng._observations = obs
    result = eng.check_readiness()
    assert result["RELIANCE"]["n"] == 10
    assert result["RELIANCE"]["EQH-Ready-1_volume"] is True


def test_9_observations_still_fails_volume_gate(tmp_path):
    eng, _ = _make_engine(tmp_path)
    obs = [_obs("RELIANCE", i, pnl=5.0) for i in range(9)]
    with eng._lock:
        eng._observations = obs
    result = eng.check_readiness()
    assert result["RELIANCE"]["EQH-Ready-1_volume"] is False


def test_evidence_fragmented_across_many_symbols_each_below_old_threshold(tmp_path):
    """Regression guard reproducing the exact confirmed-live scenario:
    18 symbols with <=6 observations each (40 total) could never clear
    a per-symbol bar of 40, but several can now clear the recalibrated
    bar of 10 once each individually accumulates enough evidence."""
    eng, _ = _make_engine(tmp_path)
    obs = []
    for i in range(10):
        obs.append(_obs("STOCKA", i, pnl=3.0))
    for i in range(6):
        obs.append(_obs("STOCKB", i, pnl=3.0))
    with eng._lock:
        eng._observations = obs
    result = eng.check_readiness()
    assert result["STOCKA"]["EQH-Ready-1_volume"] is True   # 10 >= 10
    assert result["STOCKB"]["EQH-Ready-1_volume"] is False  # 6 < 10
