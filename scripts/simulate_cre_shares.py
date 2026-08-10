"""Capital simulation for CRE strategy-share mapping (post-fix)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from risk_control.capital_risk_engine import CapitalRiskEngine, _STRATEGY_SHARE, _DEFAULT_SHARE
from config import MAX_RISK_PER_TRADE_PCT

cre = CapitalRiskEngine()

# Representative (strategy, base_strategy_label, entry_price, stop_distance)
SIGNALS = [
    ("EDG_COMPOS_92_EE0002", "Breakout_Volume", 250.0,  13.56),   # CROMPTON
    ("EDG_MOMENT_95_EE0000", "Breakout_Volume", 1300.0, 29.25),   # RELIANCE evolved
    ("Trend_Pullback",       "-",               450.0,  10.13),   # ITC
    ("Equity_Breakout",      "-",               900.0,  20.25),   # SBI
    ("Breakout_Volume",      "-",               1800.0, 40.50),   # DEEPAKNTR
    ("Mean_Reversion",       "-",               1300.0, 29.25),   # RELIANCE
    ("Momentum_Retest",      "-",               1300.0, 59.34),   # HAVELLS
]
CAPITALS = [10_000, 50_000, 1_00_000, 2_00_000, 5_00_000]
REGIME_EXP = 0.80   # typical bull regime exposure

print()
print(f"MAX_RISK_PER_TRADE_PCT = {MAX_RISK_PER_TRADE_PCT} ({MAX_RISK_PER_TRADE_PCT*100:.2f}%)")
print()

for capital in CAPITALS:
    dep = capital * REGIME_EXP
    print(f"Capital=Rs{capital:,}  Deployable=Rs{dep:,.0f}")
    header = f"  {'Strategy':<30} {'Base':<25} {'Share':>6} {'Budget':>9} {'Risk':>7} {'SL dist':>8} {'Qty':>5}  CRE"
    print(header)
    print("  " + "-" * 97)
    for strat, base_lbl, entry, sl_dist in SIGNALS:
        budget = cre._strategy_budget(strat, dep)
        share  = budget / dep
        risk   = budget * MAX_RISK_PER_TRADE_PCT
        qty_r  = int(risk / sl_dist) if sl_dist > 0 else 0
        qty_b  = int(budget / entry) if entry > 0 else 0
        qty    = min(qty_r, qty_b)
        cre_ok = "PASS" if qty > 0 else "ZERO (capital too low)"
        print(f"  {strat:<30} {base_lbl:<25} {share:.2f}  Rs{budget:>8,.0f}  Rs{risk:>5.2f}  Rs{sl_dist:>7.2f}  {qty:>4}  {cre_ok}")
    print()
