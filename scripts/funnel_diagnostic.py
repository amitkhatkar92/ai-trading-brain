"""
Deep funnel diagnostic — finds the real 290→63 drop cause.
Checks: MetaStrategy active set, min_rr thresholds, bear-market gate.

Run: python scripts/funnel_diagnostic.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("PAPER_TRADING", "true")

import logging
logging.disable(logging.WARNING)

# ── Strategy min_rr thresholds ────────────────────────────────────────────────
from strategy_lab.strategy_generator_ai import STRATEGY_PARAMS

print("Strategy min_rr thresholds (non-evolved):")
print(f"  {'Strategy':<40} min_rr")
print("  " + "-" * 52)
for name, params in sorted(STRATEGY_PARAMS.items()):
    mrr = params.get("min_rr", "NOT SET")
    print(f"  {name:<40} {mrr}")

# ── MetaStrategy active set per regime ───────────────────────────────────────
print("\nMetaStrategyController active set per regime:")
from strategy_lab.meta_strategy_controller import MetaStrategyController
from market_intelligence.market_regime_ai import RegimeLabel
from communication.market_types import MarketSnapshot, RegimeLabel as RL
from datetime import datetime

meta = MetaStrategyController()
all_strats = set(STRATEGY_PARAMS.keys())

for regime in [RL.BULL_TREND, RL.RANGE_MARKET, RL.BEAR_MARKET, RL.VOLATILE]:
    snap = MarketSnapshot(
        timestamp=datetime.now(), indices={}, regime=regime,
        volatility=None, vix=15.0, sector_flows=[], sector_leaders=[],
        events_today=[], market_breadth=0.5, pcr=1.0,
    )
    try:
        active = meta.get_active_strategies(snap, all_strats)
        active_names = sorted(active) if active else []
        blocked = sorted(all_strats - set(active_names)) if active else []
        print(f"\n  Regime: {regime.value}")
        print(f"    Active strategies : {len(active_names)}/{len(all_strats)}")
        if blocked:
            print(f"    Blocked ({len(blocked)}): {', '.join(blocked[:8])}" +
                  ("  ..." if len(blocked) > 8 else ""))
    except Exception as e:
        print(f"\n  Regime: {regime.value} — error: {e}")

# ── What the equity scanner outputs vs min_rr ────────────────────────────────
print("\n\nEquity scanner setup configs vs min_rr:")
try:
    from opportunity_engine.equity_scanner_ai import SETUPS
    for name, cfg in SETUPS.items():
        rr = cfg.get("rr", cfg.get("min_rr", "?"))
        print(f"  Setup: {name:<35} rr={rr}")
except Exception as e:
    print(f"  Could not load SETUPS: {e}")
