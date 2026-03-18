"""
Root cause diagnostic — why scanner strategies get dropped.
Run: python scripts/scanner_strategy_diagnostic.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("PAPER_TRADING", "true")

import logging
logging.disable(logging.WARNING)

from strategy_lab.strategy_generator_ai import STRATEGY_PARAMS
from strategy_lab.backtesting_ai import _BACKTEST_CACHE, BacktestingAI
from strategy_lab.meta_strategy_controller import MetaStrategyController, _REGIME_MAP
from models.market_data import RegimeLabel

# Populate backtest cache
ai = BacktestingAI()
passing_strategies = {n for n, r in _BACKTEST_CACHE.items() if r.passes_gate}
meta = MetaStrategyController()

# Scanner emits these 5 strategy names
SCANNER_STRATEGIES = [
    "Breakout_Volume",
    "Momentum_Retest",
    "Trend_Pullback",
    "Mean_Reversion",
]

print("=" * 75)
print("SCANNER STRATEGY FATE PER REGIME")
print("=" * 75)

for regime in [RegimeLabel.BULL_TREND, RegimeLabel.RANGE_MARKET,
               RegimeLabel.BEAR_MARKET, RegimeLabel.VOLATILE]:
    regime_candidates = set(_REGIME_MAP.get(regime.value, []))
    active = regime_candidates & passing_strategies
    # Include evolved variants
    for variant, base in meta._evolved_bases.items():
        if base in regime_candidates and variant in passing_strategies:
            active.add(variant)
    if regime in (RegimeLabel.BEAR_MARKET, RegimeLabel.VOLATILE):
        active.add("Hedging_Model")

    print(f"\nRegime: {regime.value}  |  Active strategies: {len(active)}")
    print(f"  Regime candidates: {sorted(regime_candidates)}")
    print(f"  Intersection with passing backtest: {len(active)} strategies")
    print()
    for strat in SCANNER_STRATEGIES:
        in_regime   = strat in regime_candidates
        passes_bt   = strat in passing_strategies
        bt_result   = _BACKTEST_CACHE.get(strat)
        in_params   = strat in STRATEGY_PARAMS
        min_rr      = STRATEGY_PARAMS.get(strat, {}).get("min_rr", "N/A") if in_params else "NOT IN PARAMS"

        # Evolved variants of this base
        evol_active = [v for v, b in meta._evolved_bases.items()
                       if b == strat and v in active]
        evol_all    = [v for v, b in meta._evolved_bases.items() if b == strat]

        if not in_params:
            fate = "⚠ NOT IN STRATEGY_PARAMS → auto_assigned by _pick_strategy"
        elif not in_regime:
            if evol_active:
                fate = f"✅ upgraded to evolved: {evol_active}"
            else:
                fate = "❌ NOT in regime map → DROPPED"
        elif not passes_bt:
            if evol_active:
                fate = f"✅ BT fail but upgraded to evolved: {evol_active}"
            else:
                failures = bt_result.failure_reasons if bt_result else ["no cache"]
                fate = f"❌ BT FAIL ({'; '.join(failures)}) + no evolved → DROPPED"
        else:
            fate = "✅ PASSES (in regime + passes backtest)"

        print(f"  {strat:<30} in_params={in_params}  in_regime={in_regime}  "
              f"passes_bt={passes_bt}  min_rr={min_rr}")
        print(f"    evolved_total={len(evol_all)}  evolved_active={len(evol_active)}")
        print(f"    → {fate}")

# ── Summary: which strategies actually pass all the way through ───────────────
print("\n" + "=" * 75)
print("RISK CONTROL DROP (63 → 14): What risk_manager.filter() does")
print("=" * 75)
try:
    from risk_control.risk_manager_ai import RiskManagerAI
    import inspect
    src = inspect.getsource(RiskManagerAI.filter)
    print("RiskManagerAI.filter() — key logic:")
    for line in src.splitlines()[:60]:
        print(line)
except Exception as e:
    print(f"Could not inspect: {e}")
