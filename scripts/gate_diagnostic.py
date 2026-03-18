"""
Per-gate failure diagnostic for BacktestingAI strategy cache.
Run: python scripts/gate_diagnostic.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("PAPER_TRADING", "true")

from strategy_lab.backtesting_ai import (
    _BACKTEST_CACHE, BacktestingAI,
    MIN_WIN_RATE, MIN_EXPECTANCY, MAX_DRAWDOWN,
    MIN_WF_CONSISTENCY, MIN_CROSS_MARKET_RATE, MAX_OVERFITTING_RATIO,
)

ai = BacktestingAI()   # populates cache

print("\nGate thresholds:")
print(f"  OOS Win Rate      >= {MIN_WIN_RATE:.0%}")
print(f"  OOS Expectancy    >= {MIN_EXPECTANCY:.3%}")
print(f"  Max Drawdown      <= {MAX_DRAWDOWN:.0%}")
print(f"  WF Consistency    >= {MIN_WF_CONSISTENCY:.0%}")
print(f"  Cross-Market      >= {MIN_CROSS_MARKET_RATE:.0%}")
print(f"  Overfitting Ratio <= {MAX_OVERFITTING_RATIO:.2f}")

HDR = f"  {'Strategy':<35} {'WinRate':>8} {'Exp%':>8} {'DD%':>7} {'WF%':>7} {'XMkt%':>7} {'OvFit':>7}  {'Gate':<6}  Failure Reasons"
print(f"\n{HDR}")
print("  " + "-" * 115)

gate_fail_counts: dict = {}
passing = failing = 0

for name, r in sorted(_BACKTEST_CACHE.items()):
    status = "PASS" if r.passes_gate else "FAIL"
    if r.passes_gate:
        passing += 1
    else:
        failing += 1
        for reason in r.failure_reasons:
            # First word is the gate label (e.g. "OOS", "WF", "Cross-mkt", "Overfit", "DD")
            label = reason.split()[0]
            gate_fail_counts[label] = gate_fail_counts.get(label, 0) + 1

    reasons = "; ".join(r.failure_reasons) if r.failure_reasons else ""
    print(
        f"  {name:<35} {r.win_rate:>8.1%} {r.expectancy:>8.3%} "
        f"{r.max_drawdown:>7.1%} {r.wf_consistency:>7.1%} "
        f"{r.cross_market_pass_rate:>7.1%} {r.overfitting_ratio:>7.2f}  "
        f"{status:<6}  {reasons}"
    )

print("  " + "-" * 115)
print(f"  PASS: {passing}   FAIL: {failing}   Total: {len(_BACKTEST_CACHE)}\n")

print("Gate failure frequency (strategies blocked by each gate):")
for gate, count in sorted(gate_fail_counts.items(), key=lambda x: -x[1]):
    pct = count / max(failing, 1) * 100
    bar = "#" * count
    print(f"  {gate:<15} : {count:>3} strategies ({pct:.0f}%)  {bar}")

print()

# ── Which ONE gate change would unlock the most signals ──────────────────────
print("Hypothetical: strategies that would pass if ONE gate were relaxed")
gates = {
    "OOS WR":    lambda r: r.win_rate             >= MIN_WIN_RATE,
    "OOS Exp":   lambda r: r.expectancy           >= MIN_EXPECTANCY,
    "Max DD":    lambda r: r.max_drawdown         <= MAX_DRAWDOWN,
    "WF Cons":   lambda r: r.wf_consistency       >= MIN_WF_CONSISTENCY,
    "Cross-Mkt": lambda r: r.cross_market_pass_rate >= MIN_CROSS_MARKET_RATE,
    "OvFit":     lambda r: r.overfitting_ratio    <= MAX_OVERFITTING_RATIO,
}

failed_strats = [r for r in _BACKTEST_CACHE.values() if not r.passes_gate]

for gate_name, gate_fn in gates.items():
    # Count how many failing strategies pass all OTHER gates (only fail this one)
    only_this = sum(
        1 for r in failed_strats
        if not gate_fn(r) and all(
            fn(r) for gn, fn in gates.items() if gn != gate_name
        )
    )
    print(f"  Removing '{gate_name}' gate alone unlocks {only_this} strategies")
